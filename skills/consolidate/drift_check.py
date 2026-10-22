#!/usr/bin/env python3
"""Code-shape metrics for a git repo, with a ratchet against a tracked baseline.

Enforced (ratchet): per-file line counts (stylesheets included), Python function lengths (exact,
via ast), and escape-hatch marker counts (`!important` included). Advisory only (check report): JS/TS
and shell function lengths (heuristic), helper names defined in several files (name match, not clone
detection), and the organization metrics in org_metrics.py (stylesheet colors and duplicate selectors,
import cycles, grab-bag modules, co-change coupling), which only `check` computes.

Coverage: a baseline records which extensions and marker keys it measured ("coverage"). Files and
markers it did not measure are advisory ("not ratcheted until rebaseline"), never regressions; a
baseline without the field measured LEGACY_EXT and LEGACY_MARKERS. The format stays version 2 and
"limits" is unchanged, so an older checker reads a newer baseline and ignores the extra entries.

    drift_check.py check      [--baseline P] [--json-out P]   report + verdict, never fails
    drift_check.py ratchet    [--baseline P]                   exit 1 on any regression, 0 otherwise
    drift_check.py rebaseline [--baseline P]                   write the baseline (explicit, user-invoked)

Paths are always relative to the git root, whatever the cwd. Baseline default:
<root>/.codeshape/baseline.json (a tracked file). Optional <root>/.codeshape/config.json:
{"file_lines": 800, "func_lines": 80, "exclude": ["glob", ...], "enforce_tests": true, "review_lines": 400,
 "exceptions": [{"path": "glob", "file_lines": 3000 | null, "func_lines": 200 | null,
                 "exempt": false, "reason": "why"}]}
(null = no limit for that aspect; exempt = skip the file entirely.)

Inline exceptions, written as a comment anywhere in the file, with a reason after the keyword:
    codeshape: allow-size <reason>        no file-size rule for this file
    codeshape: allow-functions <reason>   no function-length rule for this file
    codeshape: allow-all <reason>         skip this file
    codeshape: allow-marker <reason>      on the same line as an escape hatch: don't count it
Every exception is recorded in the metrics; new ones since the baseline are reported, never hidden.
Stdlib only; never imports or executes project code.
"""
import argparse
import ast
import collections
import datetime
import fnmatch
import json
import os
import re
import subprocess
import sys
import warnings

LEGACY_EXT = {".py", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".sh", ".bash", ".zsh"}
STYLE_EXT = {".css", ".scss", ".sass", ".less"}  # file-size rule and the `important` marker only
SOURCE_EXT = LEGACY_EXT | STYLE_EXT
DEFAULT_EXCLUDE = ["node_modules/**", "**/node_modules/**", "dist/**", "**/dist/**", "build/**", "**/build/**",
                   "vendor/**", "**/vendor/**", "**/__pycache__/**", "**/*.min.*", "**/generated/**", "**/*.generated.*"]
DEFAULTS = {"file_lines": 800, "func_lines": 80, "exclude": [], "enforce_tests": True, "exceptions": [],
            "review_lines": 400}  # review_lines is read by stop_hook.py; 0 turns the review trigger off
INLINE_EXC = re.compile(r"codeshape:\s*allow-(size|functions|all)\b[ \t:,-]*(.*)")
INLINE_MARKER_EXC = re.compile(r"codeshape:\s*allow-marker\b")
# Names that legitimately exist in many files; not evidence of copy-paste.
COMMON_NAMES = {
    "main", "run", "setup", "teardown", "setUp", "tearDown", "setUpClass", "tearDownClass", "register",
    "parse_args", "build_parser", "parser", "handler", "default", "usage", "cli", "init", "cleanup", "fail",
    "log", "__init__", "__repr__", "__str__", "__enter__", "__exit__", "render", "App", "create", "load", "save",
}
MARKERS = {
    "sys_path_hack": re.compile(r"sys\.path\.(insert|append)\("),
    "dual_import_guard": re.compile(r"^\s*if __package__"),
    "ts_any": re.compile(r"(:\s*any\b|\bas any\b|<any>)"),
    "type_ignore": re.compile(r"#\s*type:\s*ignore|@ts-ignore|@ts-expect-error"),
    "lint_disable": re.compile(r"eslint-disable|noqa|pylint:\s*disable"),
    "bare_except": re.compile(r"^\s*except\s*:"),
    "important": re.compile(r"!\s*important\b", re.IGNORECASE),
}
# A substring every match of the marker contains: files without one skip that marker's line scan.
MARKER_HINTS = {"sys_path_hack": ("sys.path.",), "dual_import_guard": ("__package__",), "ts_any": ("any",),
                "type_ignore": ("ignore", "@ts-expect-error"), "lint_disable": ("disable", "noqa"),
                "bare_except": ("except",), "important": ("important",)}
LEGACY_MARKERS = {"sys_path_hack", "dual_import_guard", "ts_any", "type_ignore", "lint_disable", "bare_except"}
# Top-level baseline keys other tools write (backend-layout's check_layout.py rebaseline); kept across rebaselines.
FOREIGN_KEYS = ("layout",)
STYLE_MARKERS = {"important"}  # counted in stylesheets only; the others in scripts only
JS_FUNC = re.compile(
    r"^\s*(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s*\*?\s*([A-Za-z_$][\w$]*)\s*\("
    r"|^\s*(?:export\s+)?(?:const|let)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s+)?(?:function\b|\([^)]*\)\s*(?::[^=]+)?=>|[A-Za-z_$][\w$]*\s*=>)"
    r"|^\s+(?:(?:public|private|protected|static|async|readonly)\s+)*([A-Za-z_$][\w$]*)\s*\([^)]*\)\s*(?::[^{]+)?\{\s*$"
)
JS_KEYWORDS = {"if", "for", "while", "switch", "catch", "function", "return", "else", "do", "with", "constructor"}
SH_FUNC = re.compile(r"^\s*(?:function\s+)?([A-Za-z_][\w:-]*)\s*\(\)\s*\{?\s*$|^\s*function\s+([A-Za-z_][\w:-]*)\s*\{?\s*$")
TEST_FILE = re.compile(r"(^|/)(tests?|__tests__|spec)/|(^|/)(test_[^/]*\.py|[^/]*_test\.py|conftest\.py|[^/]*\.(test|spec)\.[cm]?[jt]sx?)$")


# ---------- git ----------

def git(repo, *args):
    r = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True, check=False)
    return r.stdout if r.returncode == 0 else ""


def git_root(path):
    return git(path, "rev-parse", "--show-toplevel").strip() or None


def renames_since(root, sha):
    """old path -> new path for files git sees as renamed between <sha> and the working tree."""
    out = git(root, "diff", "-M", "--name-status", sha)
    mapping = {}
    for line in out.splitlines():
        parts = line.split("\t")
        if parts and parts[0].startswith("R") and len(parts) == 3:
            mapping[parts[1]] = parts[2]
    return mapping


# ---------- config ----------

def load_config(root):
    cfg = dict(DEFAULTS)
    p = os.path.join(root, ".codeshape", "config.json")
    try:
        with open(p, encoding="utf-8") as fh:
            user = json.load(fh)
        for k in DEFAULTS:
            if k in user:
                cfg[k] = user[k]
    except FileNotFoundError:
        pass
    except (OSError, ValueError) as e:
        cfg["config_error"] = f"{p}: {e}"
    cfg["exclude"] = DEFAULT_EXCLUDE + list(cfg["exclude"])
    return cfg


def excluded(path, patterns):
    return any(fnmatch.fnmatch(path, pat) for pat in patterns)


def is_test(path):
    return bool(TEST_FILE.search(path))


# ---------- measurement ----------

def source_files(root, cfg):
    listed = git(root, "ls-files") + git(root, "ls-files", "--others", "--exclude-standard")
    for path in dict.fromkeys(listed.splitlines()):
        if os.path.splitext(path)[1] in SOURCE_EXT and not excluded(path, cfg["exclude"]):
            yield path


def python_functions(text):
    """(name, line, length) for every def; name is qualified with the class for methods."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        tree = ast.parse(text)
    funcs = []

    def walk(node, prefix):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                funcs.append((prefix + child.name, child.lineno, (child.end_lineno or child.lineno) - child.lineno + 1))
                walk(child, prefix + child.name + ".")
            elif isinstance(child, ast.ClassDef):
                walk(child, prefix + child.name + ".")
            else:
                walk(child, prefix)
    walk(tree, "")
    top = [n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    return funcs, top


def brace_span(lines, start):
    """Lines in the brace block that begins after the signature's parameter list on lines[start]."""
    depth, opened = 0, False
    for i in range(start, len(lines)):
        line = re.sub(r"(['\"`])(?:\\.|(?!\1).)*\1", "", lines[i]).split("//")[0]
        if i == start and ")" in line:
            line = line[line.rfind(")") + 1:]  # skip braces inside the parameter list
        for ch in line:
            if ch == "{":
                depth += 1
                opened = True
            elif ch == "}":
                depth -= 1
                if opened and depth == 0:
                    return i - start + 1
        if not opened and i - start > 3:
            return 1
    return len(lines) - start


def js_functions(lines):
    funcs, top = [], []
    for i, line in enumerate(lines):
        m = JS_FUNC.match(line)
        if not m:
            continue
        name = m.group(1) or m.group(2) or m.group(3)
        if name in JS_KEYWORDS:
            continue
        funcs.append((name, i + 1, brace_span(lines, i)))
        if not line.startswith((" ", "\t")):
            top.append(name)
    return funcs, top


def sh_functions(lines):
    funcs, top = [], []
    for i, line in enumerate(lines):
        m = SH_FUNC.match(line)
        if not m:
            continue
        name = m.group(1) or m.group(2)
        end = next((j for j in range(i + 1, len(lines)) if re.match(r"^\s*}\s*$", lines[j])), i)
        funcs.append((name, i + 1, end - i + 1))
        top.append(name)
    return funcs, top


def file_exception(path, text, cfg):
    """Effective per-file limits from config exceptions and inline directives.
    Returns (skip, file_limit_or_None, func_limit_or_None, record_or_None)."""
    flim, fnlim, rec = cfg["file_lines"], cfg["func_lines"], None
    for e in cfg["exceptions"]:
        if not fnmatch.fnmatch(path, e.get("path", "")):
            continue
        rec = {"source": "config", "reason": str(e.get("reason", "")).strip() or "(no reason given)"}
        if e.get("exempt"):
            return True, None, None, dict(rec, kind="exempt")
        if "file_lines" in e:
            flim = e["file_lines"]
        if "func_lines" in e:
            fnlim = e["func_lines"]
        rec["kind"] = ",".join(k for k in ("file_lines", "func_lines") if k in e) or "noop"
    m = INLINE_EXC.search(text)
    if m:
        kind, reason = m.group(1), m.group(2).strip().rstrip("*/").strip() or "(no reason given)"
        rec = {"source": "inline", "kind": "allow-" + kind, "reason": reason}
        if kind == "all":
            return True, None, None, rec
        if kind == "size":
            flim = None
        if kind == "functions":
            fnlim = None
    return False, flim, fnlim, rec


def measure(root, cfg):
    files, py_funcs, heuristic_funcs, defs = {}, {}, [], collections.defaultdict(set)
    markers, parse_errors, tests = collections.Counter(), [], set()
    file_limits, func_limits, exceptions = {}, {}, {}
    for path in source_files(root, cfg):
        try:
            with open(os.path.join(root, path), encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError as e:
            parse_errors.append(f"{path}: {e}")
            continue
        skip, flim, fnlim, rec = file_exception(path, text, cfg)
        if rec:
            exceptions[path] = rec
        if skip:
            continue
        if flim != cfg["file_lines"]:
            file_limits[path] = flim
        if fnlim != cfg["func_lines"]:
            func_limits[path] = fnlim
        lines = text.splitlines()
        files[path] = len(lines)
        test = is_test(path)
        if test:
            tests.add(path)
        ext = os.path.splitext(path)[1]
        top = []
        if ext in STYLE_EXT:
            if not test and "important" in text.lower():
                markers["important"] += sum(1 for ln in lines if MARKERS["important"].search(ln)
                                            and not INLINE_MARKER_EXC.search(ln))
            continue  # no function rule, no helper names, no script markers for stylesheets
        if ext == ".py":
            try:
                funcs, top = python_functions(text)
                py_funcs[path] = {name: length for name, _, length in funcs}
            except (SyntaxError, ValueError) as e:
                parse_errors.append(f"{path}: {e.__class__.__name__}")
        else:
            funcs, top = sh_functions(lines) if ext in {".sh", ".bash", ".zsh"} else js_functions(lines)
            for name, line_no, length in funcs:
                if fnlim is not None and length > fnlim:
                    heuristic_funcs.append({"file": path, "name": name, "line": line_no, "lines": length})
        if not test:
            for name in top:
                if name not in COMMON_NAMES and not name.startswith(("test_", "_test")):
                    defs[name].add(path)
            for key, rx in MARKERS.items():
                if key in STYLE_MARKERS or (key == "ts_any" and ext not in {".ts", ".tsx"}):
                    continue
                if not any(h in text for h in MARKER_HINTS[key]):
                    markers[key] += 0  # keep the key, as the full scan would
                    continue
                markers[key] += sum(1 for ln in lines if rx.search(ln) and not INLINE_MARKER_EXC.search(ln))
    heuristic_funcs.sort(key=lambda f: -f["lines"])
    return {
        "version": 2,
        "head": git(root, "rev-parse", "HEAD").strip(),
        "date": datetime.date.today().isoformat(),
        "limits": {"file_lines": cfg["file_lines"], "func_lines": cfg["func_lines"], "enforce_tests": cfg["enforce_tests"]},
        "coverage": {"extensions": sorted(SOURCE_EXT), "markers": sorted(MARKERS)},
        "files": files,
        "tests": sorted(tests),
        "py_funcs": py_funcs,
        "markers": dict(markers),
        "file_limits": file_limits,
        "func_limits": func_limits,
        "exceptions": exceptions,
        "advisory": {
            "heuristic_long_functions": heuristic_funcs,
            "duplicate_names": {n: sorted(p) for n, p in defs.items() if len(p) > 1},
        },
        "parse_errors": parse_errors,
    }


# ---------- comparison ----------

def file_limit(m, path):
    return m.get("file_limits", {}).get(path, m["limits"]["file_lines"])  # None: no size rule


def func_limit(m, path):
    return m.get("func_limits", {}).get(path, m["limits"]["func_lines"])


def over_limit_functions(m, path):
    lim = func_limit(m, path)
    if lim is None:
        return {}
    return {name: n for name, n in m["py_funcs"].get(path, {}).items() if n > lim}


def covered_extensions(base):
    return set((base or {}).get("coverage", {}).get("extensions") or LEGACY_EXT)


def covered_markers(base):
    return set((base or {}).get("coverage", {}).get("markers") or LEGACY_MARKERS)


def uncovered(cur, base):
    """What the baseline did not measure: (files over the limit, {marker: count}). Advisory until rebaseline."""
    exts, keys = covered_extensions(base), covered_markers(base)
    files = sorted(((p, n) for p, n in cur["files"].items() if os.path.splitext(p)[1] not in exts
                    and file_limit(cur, p) is not None and n > file_limit(cur, p)), key=lambda x: -x[1])
    return files, {k: v for k, v in sorted(cur["markers"].items()) if k not in keys and v}


def ratchet(cur, base, renames):
    """Independent rules: a file over the limit may not grow; a Python function over the limit may
    not grow; no new over-limit function; marker totals may not rise. Allowances follow renames.
    Extensions and marker keys the baseline did not cover are skipped here (see uncovered())."""
    if cur["limits"] != base["limits"]:
        return [f"limits changed since baseline ({base['limits']} -> {cur['limits']}); run rebaseline"], [], True, []
    worse, better = [], []
    skip_tests = not cur["limits"]["enforce_tests"]
    old_for = {new: old for old, new in renames.items()}
    exts, keys = covered_extensions(base), covered_markers(base)
    for path, n in sorted(cur["files"].items()):
        if (skip_tests and path in cur["tests"]) or os.path.splitext(path)[1] not in exts:
            continue
        old = old_for.get(path, path)
        b = base["files"].get(old)
        flim = file_limit(cur, path)
        if flim is None:
            continue
        if n > flim and (b is None or n > b):
            if b is None:
                worse.append(f"{path}: new file is {n} lines (limit {flim}); split it before it lands")
            elif b <= flim:
                worse.append(f"{path}: crossed {flim} lines ({b} -> {n})")
            else:
                worse.append(f"{path}: already over {flim} lines and grew ({b} -> {n}); put new code beside it")
        elif b is not None and n < b and b > flim:
            better.append(f"{path}: {b} -> {n}")
        cf, bf = over_limit_functions(cur, path), over_limit_functions(base, old) if old in base["py_funcs"] else {}
        for name, length in sorted(cf.items()):
            bl = bf.get(name)
            if bl is None:
                worse.append(f"{path}: {name} is {length} lines (limit {func_limit(cur, path)}); new or newly over the limit")
            elif length > bl:
                worse.append(f"{path}: {name} grew {bl} -> {length} lines (already over the limit)")
            elif length < bl:
                better.append(f"{path}: {name} {bl} -> {length}")
    for k, v in sorted(cur["markers"].items()):
        if k not in keys:
            continue
        b = base["markers"].get(k, 0)
        if v > b:
            worse.append(f"marker {k}: {b} -> {v} (sys.path hacks, `as any`, type-ignore, lint-disable, bare except, "
                         f"!important)")
        elif v < b:
            better.append(f"marker {k}: {b} -> {v}")
    base_exc = base.get("exceptions", {})
    new_exc = [f"{p}: {e['kind']} ({e['source']}) {e['reason']}" for p, e in sorted(cur["exceptions"].items())
               if base_exc.get(old_for.get(p, p)) != e]
    return worse, better, False, new_exc


# ---------- modes ----------

def write_json(path, data):
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=1, sort_keys=True)
        fh.write("\n")
    os.replace(tmp, path)


def load_json(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        return None


def report(cur, base, renames):
    lim = cur["limits"]
    over = sorted(((p, n) for p, n in cur["files"].items() if n > lim["file_lines"]), key=lambda x: -x[1])
    longf = sorted(((p, n, l) for p, fs in cur["py_funcs"].items() for n, l in fs.items() if l > lim["func_lines"]), key=lambda x: -x[2])
    print(f"HEAD {cur['head'][:8]}  {cur['date']}  {len(cur['files'])} source files, {sum(cur['files'].values())} lines"
          f"  (limits: {lim['file_lines']}/file, {lim['func_lines']}/function)")
    if cur["parse_errors"]:
        print(f"unparsable: {len(cur['parse_errors'])} file(s) not measured: " + "; ".join(cur["parse_errors"][:5]))
    print(f"\nfiles over {lim['file_lines']} lines: {len(over)}")
    for p, n in over[:12]:
        print(f"  {n:6}  {p}")
    print(f"\npython functions over {lim['func_lines']} lines: {len(longf)} (top 10)")
    for p, n, l in longf[:10]:
        print(f"  {l:6}  {p}  {n}")
    adv = cur["advisory"]
    print(f"\nadvisory, JS/TS/shell functions over the limit (heuristic): {len(adv['heuristic_long_functions'])} (top 5)")
    for f in adv["heuristic_long_functions"][:5]:
        print(f"  {f['lines']:6}  {f['file']}:{f['line']}  {f['name']}")
    print(f"advisory, helper names defined in 2+ non-test files: {len(adv['duplicate_names'])} (top 8)")
    for n, paths in sorted(adv["duplicate_names"].items(), key=lambda kv: -len(kv[1]))[:8]:
        print(f"  {len(paths):3}x  {n}")
    print("\nmarkers: " + ", ".join(f"{k}={v}" for k, v in sorted(cur["markers"].items())))
    if cur["exceptions"]:
        print(f"\nexceptions in force: {len(cur['exceptions'])}")
        for p, e in sorted(cur["exceptions"].items())[:10]:
            print(f"  {p}: {e['kind']} ({e['source']}) {e['reason']}")
    if "organization" in adv:
        import org_metrics  # check only; the ratchet path (every hooked turn) never loads it
        org_metrics.print_report(adv["organization"])
    print_grandfather(cur, base)
    if not base:
        print("\nverdict: NO BASELINE (run `rebaseline` to start enforcing)")
        return
    worse, better, incompatible, new_exc = ratchet(cur, base, renames)
    print(f"\nsince baseline {base['head'][:8]} ({base['date']}): {len(worse)} regression(s), "
          f"{len(better)} improvement(s), {len(new_exc)} new exception(s)")
    for w in worse[:15]:
        print(f"  WORSE   {w}")
    for b in better[:8]:
        print(f"  better  {b}")
    for e in new_exc[:8]:
        print(f"  EXCEPTION  {e}")
    verdict = "RECOMMENDED" if (worse and not incompatible) else "NOT NEEDED"
    print(f"\nverdict: consolidation {verdict}")


def print_grandfather(cur, base):
    files, marks = uncovered(cur, base)
    if not files and not marks:
        return
    print(f"\nrebaseline would grandfather (not ratcheted until rebaseline; afterwards ratcheted at their "
          f"current size): {len(files)} uncovered file(s) over the limit, markers "
          + (", ".join(f"{k}={v}" for k, v in marks.items()) or "none"))
    for p, n in files[:12]:
        print(f"  {n:6}  {p}")


def uncovered_note(cur, base):
    files, marks = uncovered(cur, base)
    if files or marks:
        what = [f"{len(files)} file(s) over the limit"] if files else []
        what += [f"marker {k}={v}" for k, v in marks.items()]
        print(f"ratchet: not ratcheted until rebaseline (the baseline predates them): {', '.join(what)}")


def implicit_baseline(cur):
    """The empty baseline a clean repo without .codeshape/baseline.json is held to."""
    return {"version": 2, "head": "", "date": "none", "limits": cur["limits"], "files": {}, "tests": [],
            "py_funcs": {}, "markers": dict(cur["markers"]), "exceptions": dict(cur["exceptions"]),
            "coverage": cur["coverage"]}


def run_check(root, cur, base, renames, json_out):
    import org_metrics  # check only; the ratchet path (every hooked turn) never loads it
    cur["advisory"]["organization"] = org_metrics.collect(root, cur, STYLE_EXT)
    report(cur, base, renames)
    if json_out:
        write_json(json_out, cur)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=["check", "ratchet", "rebaseline"])
    ap.add_argument("--repo", default=".", help="any path inside the repo (default: cwd)")
    ap.add_argument("--baseline", help="baseline file (default: <git root>/.codeshape/baseline.json)")
    ap.add_argument("--json-out", help="check: also write this run's metrics here")
    ap.add_argument("--allow-dirty", action="store_true",
                    help="rebaseline: allow uncommitted changes (normally refused, since they may not survive)")
    args = ap.parse_args()

    root = git_root(args.repo)
    if not root:
        print(f"not inside a git repository: {os.path.abspath(args.repo)}", file=sys.stderr)
        sys.exit(2)
    cfg = load_config(root)
    if "config_error" in cfg:
        print(f"config error: {cfg['config_error']}", file=sys.stderr)
        sys.exit(2)
    baseline_path = args.baseline or os.path.join(root, ".codeshape", "baseline.json")
    base = load_json(baseline_path)
    if base is not None and base.get("version") != 2:
        print(f"baseline {baseline_path} is an older format; run rebaseline", file=sys.stderr)
        base = None
    cur = measure(root, cfg)
    renames = renames_since(root, base["head"]) if base and base.get("head") else {}

    if args.mode == "rebaseline":
        dirty = [ln[3:] for ln in git(root, "status", "--porcelain").splitlines()
                 if ln[3:] and not ln[3:].startswith(".codeshape/")]
        if dirty and not args.allow_dirty:
            print(f"rebaseline refused: {len(dirty)} uncommitted change(s) (e.g. {dirty[0]}). The baseline would "
                  f"record work that may still change or be discarded. Commit first, or pass --allow-dirty.",
                  file=sys.stderr)
            sys.exit(2)
        previous = load_json(baseline_path) or {}
        cur.update({key: previous[key] for key in FOREIGN_KEYS if key in previous})
        write_json(baseline_path, cur)
        rel = os.path.relpath(baseline_path, root)
        print(f"baseline written: {rel} at HEAD {cur['head'][:8]} ({len(cur['files'])} files). "
              f"Commit it when you commit; the ratchet compares against it from now on.")
        return

    if args.mode == "ratchet":
        implicit = False
        if base is None:
            # "Clean" is judged on committed files only, so a new or edited file that is over the
            # limit counts as a regression rather than as a reason to stay silent.
            dirty = set()
            for line in git(root, "status", "--porcelain", "--untracked-files=all").splitlines():
                dirty.add(line[3:].split(" -> ")[-1])
            over = [p for p, n in cur["files"].items() if n > cfg["file_lines"] and p not in dirty]
            over += [p for p in cur["py_funcs"] if over_limit_functions(cur, p) and p not in dirty]
            if over:
                print(f"ratchet: no baseline at {os.path.relpath(baseline_path, root)} and {len(set(over))} file(s) "
                      f"already over the limits; not enforced. Run `consolidate rebaseline` when the tree is in a "
                      f"state worth grandfathering.")
                return
            # Clean repo: enforce size rules against an empty baseline so new repos need no setup.
            base = implicit_baseline(cur)
            implicit = True
        worse, better, incompatible, new_exc = ratchet(cur, base, renames)
        if incompatible:
            print("ratchet: " + worse[0])
            return
        uncovered_note(cur, base)
        for e in new_exc:
            print(f"EXCEPTION  {e}")
        for w in worse:
            print(f"WORSE  {w}")
        if worse:
            where = "the implicit empty baseline (clean repo, no .codeshape/baseline.json)" if implicit else f"baseline {base['head'][:8]}"
            print(f"ratchet: {len(worse)} regression(s) vs {where}. Fix within the task's scope "
                  f"(move the new code beside the big file, drop the escape hatch); do not restructure unrelated "
                  f"code to satisfy the metric. If the growth is deliberate and reviewed, run rebaseline.")
            sys.exit(1)
        if better and not implicit:
            print(f"ratchet: ok; {len(better)} improvement(s). Run rebaseline to lock them in.")
        return

    run_check(root, cur, base, renames, args.json_out)


if __name__ == "__main__":
    main()
