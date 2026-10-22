#!/usr/bin/env python3
"""Save conversation-summary pages ("codex Artifacts") into the local store.

Agents write only the page body. This script wraps it in the shared template,
keeps the store's index.html current, and prunes pages untouched for
PRUNE_DAYS. Pages in pinned/ are never pruned. Standard library only, so the
same file runs on the Mac and the Pi.
"""

import argparse
import datetime as dt
import html
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

PRUNE_DAYS = 90
STORE = Path(os.environ.get("AGENT_ART_DIR", Path.home() / ".agent" / "artifacts"))
PINNED = STORE / "pinned"
INDEX = STORE / "index.html"
# The Mac mounts the Pi's home over SMB here, so Pi pages can be opened there.
PI_HOME = Path("/home/<user>")
PI_MOUNT_ON_MAC = Path("/Volumes/<shared-volume>")

LIGHT = """
  --bg: #fbfbfa; --fg: #1d1d1f; --muted: #5f5f66; --line: #deded9;
  --panel: #f1f1ed; --accent: #2457c5; --ok: #1d7a38; --warn: #8f5b00;
  --bad: #b3261e;"""
DARK = """
  --bg: #161618; --fg: #e7e7ea; --muted: #a0a0a8; --line: #33333a;
  --panel: #202024; --accent: #8fb0ff; --ok: #6fcf8a; --warn: #e6b450;
  --bad: #ff8a80; color-scheme: dark;"""

CSS = f"""
:root {{ color-scheme: light;{LIGHT} }}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{{DARK} }} }}
:root[data-theme="dark"] {{{DARK} }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; background: var(--bg); color: var(--fg);
  font: 16px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif; }}
.page {{ max-width: 54rem; margin: 0 auto; padding-block: 20px 48px;
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); }}
h1, h2, h3 {{ text-wrap: balance; }}
h1 {{ font-size: 1.6rem; line-height: 1.25; margin: 0.2rem 0 0.3rem; }}
h2 {{ font-size: 1.2rem; margin: 2rem 0 0.6rem; padding-top: 1rem; border-top: 1px solid var(--line); }}
h3 {{ font-size: 1.02rem; margin: 1.4rem 0 0.4rem; }}
a {{ color: var(--accent); }}
.meta, nav {{ color: var(--muted); font-size: 0.9rem; }}
nav a {{ text-decoration: none; }}
code, pre {{ font: 0.88em/1.45 ui-monospace, SFMono-Regular, Menlo, monospace; }}
code {{ background: var(--panel); padding: 0.1em 0.3em; border-radius: 4px; overflow-wrap: anywhere; }}
pre {{ background: var(--panel); padding: 12px 14px; border-radius: 6px; overflow-x: auto; }}
pre code {{ background: none; padding: 0; overflow-wrap: normal; }}
table {{ display: block; overflow-x: auto; border-collapse: collapse; margin: 0.8rem 0; font-size: 0.94rem; }}
th, td {{ font-variant-numeric: tabular-nums; text-align: left; vertical-align: top; padding: 6px 10px; border-bottom: 1px solid var(--line); }}
th {{ color: var(--muted); font-weight: 600; }}
.callout {{ border-left: 3px solid var(--accent); background: var(--panel); padding: 10px 14px; border-radius: 0 6px 6px 0; }}
.ok, .warn, .bad {{ font-weight: 600; font-size: 0.85em; padding: 0.05em 0.45em; border-radius: 4px; border: 1px solid currentColor; }}
.ok {{ color: var(--ok); }} .warn {{ color: var(--warn); }} .bad {{ color: var(--bad); }}
a:focus-visible, input:focus-visible, summary:focus-visible {{ outline: 2px solid var(--accent); outline-offset: 2px; }}
details {{ margin: 0.6rem 0; }} summary {{ cursor: pointer; }}
input[type=search] {{ width: 100%; max-width: 24rem; font: inherit; padding: 6px 10px; margin: 0.6rem 0;
  color: var(--fg); background: var(--panel); border: 1px solid var(--line); border-radius: 6px; }}
"""

# The index link only works from the local store, so drop it once the page is
# hosted elsewhere (e.g. published as a Claude Artifact).
LOCAL_NAV_JS = """
<script>
if (location.protocol !== "file:") document.querySelectorAll(".local-only").forEach(e => e.remove());
else if (location.pathname.includes("/pinned/")) document.querySelectorAll("a[data-index]").forEach(a => a.href = "../index.html");
</script>"""

META_RE = re.compile(r'<meta name="agent-art-([a-z]+)" content="([^"]*)">')
TITLE_RE = re.compile(r"<title>(.*?)</title>", re.S | re.I)
FULL_DOC_RE = re.compile(r"^\s*(<!doctype|<html|<head|<body)", re.I)


def now() -> dt.datetime:
    return dt.datetime.now().replace(second=0, microsecond=0)


def slugify(text: str, limit: int = 48) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:limit].rstrip("-") or "page"


def detect_project(cwd: Path) -> str:
    try:
        top = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=cwd,
                             capture_output=True, text=True, timeout=5)
        if top.returncode == 0 and top.stdout.strip():
            return slugify(Path(top.stdout.strip()).name, 24)
    except (OSError, subprocess.SubprocessError):
        pass
    return "home" if cwd == Path.home() else slugify(cwd.name, 24)


def tilde(path: Path) -> str:
    home = str(Path.home())
    text = str(path)
    return "~" + text[len(home):] if text == home or text.startswith(home + "/") else text


def write_atomic(path: Path, text: str) -> None:
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp-", suffix=".html")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(text)
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)


def ensure_store() -> None:
    PINNED.mkdir(parents=True, exist_ok=True)
    for d in (STORE, PINNED):
        if d.stat().st_mode & 0o777 != 0o700:
            os.chmod(d, 0o700)


def read_meta(path: Path) -> dict:
    head = path.read_text(encoding="utf-8", errors="replace")[:4000]
    meta = dict(META_RE.findall(head))
    title = TITLE_RE.search(head)
    meta["title"] = html.unescape(title.group(1).strip()) if title else path.stem
    return meta


def full_document(head: str, content: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
{head}
</head>
<body>
{content}
</body>
</html>
"""


def page_parts(title: str, body: str, meta: dict) -> tuple:
    """Return the page's (head, content). The hosted copy for a Claude Artifact
    is just these two joined, since the Artifact host adds its own skeleton."""
    esc = {k: html.escape(v, quote=True) for k, v in meta.items()}
    created = dt.datetime.fromisoformat(meta["created"])
    stamp = created.strftime("%-d %b %Y %H:%M")
    if meta["updated"] != meta["created"]:
        stamp += " · updated " + dt.datetime.fromisoformat(meta["updated"]).strftime("%-d %b %H:%M")
    meta_tags = "\n".join(f'<meta name="agent-art-{k}" content="{v}">' for k, v in esc.items())
    head = f"""<title>{html.escape(title)}</title>
<meta name="claude:viewport-fit-sides" content="cover">
{meta_tags}
<style>{CSS}</style>"""
    content = f"""<div class="page">
<nav class="local-only"><a href="index.html" data-index>All artifacts</a></nav>
<h1>{html.escape(title)}</h1>
<p class="meta">{stamp} · {esc['project']} · {esc['agent']} · <code>{esc['cwd']}</code></p>
<main>
{body.strip()}
</main>
</div>{LOCAL_NAV_JS}"""
    return head, content


def pages_in(folder: Path) -> list:
    # Skip index.html and in-flight .tmp-* files from a concurrent save.
    return [p for p in folder.glob("*.html") if p != INDEX and not p.name.startswith(".")]


def page_paths() -> list:
    return pages_in(STORE) + pages_in(PINNED)


def prune() -> list:
    cutoff = dt.datetime.now().timestamp() - PRUNE_DAYS * 86400
    gone = [p for p in pages_in(STORE) if p.stat().st_mtime < cutoff]
    for p in gone:
        p.unlink()
    return gone


def index_rows(pages: list) -> str:
    rows = []
    for p in sorted(pages, key=lambda p: p.stat().st_mtime, reverse=True):
        m = read_meta(p)
        updated = dt.datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        href = html.escape(p.relative_to(STORE).as_posix(), quote=True)
        rows.append(f"<tr><td>{updated}</td><td><a href=\"{href}\">{html.escape(m['title'])}</a></td>"
                    f"<td>{html.escape(m.get('project', ''))}</td><td>{html.escape(m.get('agent', ''))}</td></tr>")
    return "\n".join(rows)


def write_index() -> None:
    pinned = pages_in(PINNED)
    recent = pages_in(STORE)
    head = "<tr><th>Updated</th><th>Title</th><th>Project</th><th>Agent</th></tr>"
    sections = []
    if pinned:
        sections.append(f"<h2>Pinned</h2>\n<table>{head}\n{index_rows(pinned)}\n</table>")
    sections.append(f"<h2>Recent</h2>\n<table>{head}\n{index_rows(recent) or '<tr><td colspan=4>None yet.</td></tr>'}\n</table>")
    body = "\n".join(sections)
    head = f"<title>Agent artifacts</title>\n<style>{CSS}</style>"
    content = f"""<div class="page">
<h1>Agent artifacts</h1>
<p class="meta">{len(recent) + len(pinned)} pages on {html.escape(os.uname().nodename)}. Pages untouched for {PRUNE_DAYS} days are deleted; pages in <code>pinned/</code> are kept.</p>
<input type="search" placeholder="Filter" aria-label="Filter pages">
{body}
</div>
<script>
const box = document.querySelector("input[type=search]");
box.addEventListener("input", () => {{
  const q = box.value.toLowerCase();
  document.querySelectorAll("tr").forEach(r => {{ if (r.querySelector("td")) r.hidden = !r.textContent.toLowerCase().includes(q); }});
}});
</script>"""
    write_atomic(INDEX, full_document(head, content))


def report(path: Path) -> None:
    print(f"path: {path}")
    print(f"url: {path.as_uri()}")
    if Path.home() == PI_HOME:
        print(f"mac: {PI_MOUNT_ON_MAC / path.relative_to(PI_HOME)}")
    print(f"index: {INDEX.as_uri()}")


def resolve_existing(raw: str) -> Path:
    path = Path(raw).expanduser().resolve()
    if path.parent not in (STORE.resolve(), PINNED.resolve()) or path == INDEX.resolve():
        sys.exit(f"agent_art: {path} is not a page in {STORE}")
    return path


def cmd_save(args) -> None:
    body = Path(args.input).read_text(encoding="utf-8") if args.input else sys.stdin.read()
    if not body.strip():
        sys.exit("agent_art: empty body")
    if FULL_DOC_RE.match(body):
        sys.exit("agent_art: send only the body fragment; the template adds <html>, <head>, the <h1> and styles")
    ensure_store()
    stamp = now()
    cwd = Path.cwd()
    meta = {"project": args.project or detect_project(cwd), "agent": args.agent,
            "created": stamp.isoformat(), "updated": stamp.isoformat(), "cwd": tilde(cwd)}
    if args.out:
        path = resolve_existing(args.out)
        if path.exists():
            meta["created"] = read_meta(path).get("created", meta["created"])
    else:
        base = f"{stamp:%Y%m%d-%H%M}-{meta['project']}-{slugify(args.slug or args.title)}"
        path, n = STORE / f"{base}.html", 2
        while path.exists():
            path, n = STORE / f"{base}-{n}.html", n + 1
    head, content = page_parts(args.title, body, meta)
    write_atomic(path, full_document(head, content))
    if args.hosted:
        hosted = Path(args.hosted).expanduser()
        hosted.parent.mkdir(parents=True, exist_ok=True)
        hosted.write_text(f"{head}\n{content}\n", encoding="utf-8")
    pruned = prune()
    write_index()
    report(path)
    if args.hosted:
        print(f"hosted: {Path(args.hosted).expanduser()}")
    if pruned:
        print(f"pruned: {len(pruned)} page(s) older than {PRUNE_DAYS} days")


def cmd_pin(args) -> None:
    src = resolve_existing(args.page)
    if src.parent == PINNED.resolve():
        sys.exit(f"agent_art: already pinned: {src}")
    dest = PINNED / src.name
    os.replace(src, dest)
    write_index()
    report(dest)


def cmd_list(args) -> None:
    if not STORE.exists():
        return
    for p in sorted(page_paths(), key=lambda p: p.stat().st_mtime, reverse=True)[: args.n]:
        m = read_meta(p)
        when = dt.datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        print(f"{when}  {m.get('project', '-'):<16} {m['title']}\n    {p}")


def cmd_index(_args) -> None:
    ensure_store()
    pruned = prune()
    write_index()
    print(f"index: {INDEX.as_uri()}")
    if pruned:
        print(f"pruned: {len(pruned)} page(s) older than {PRUNE_DAYS} days")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    save = sub.add_parser("save", help="wrap a body fragment (stdin or --input) and save it")
    save.add_argument("--title", required=True, help="plain page name, 2-4 words")
    save.add_argument("--slug", help="filename slug (default: from the title)")
    save.add_argument("--project", help="project label (default: git toplevel or cwd name)")
    save.add_argument("--agent", default="codex", help="codex or claude")
    save.add_argument("--input", help="read the body fragment from this file instead of stdin")
    save.add_argument("--out", help="existing page to overwrite (re-running +art in the same conversation)")
    save.add_argument("--hosted", help="also write a copy without the document skeleton, for publishing as a Claude Artifact")
    save.set_defaults(func=cmd_save)
    pin = sub.add_parser("pin", help="move a page into pinned/ so it is never pruned")
    pin.add_argument("page")
    pin.set_defaults(func=cmd_pin)
    lst = sub.add_parser("list", help="show the most recent pages")
    lst.add_argument("-n", type=int, default=15)
    lst.set_defaults(func=cmd_list)
    sub.add_parser("index", help="prune and rebuild index.html").set_defaults(func=cmd_index)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
