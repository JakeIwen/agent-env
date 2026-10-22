"""Advisory stylesheet metrics for drift_check.py `check`: color literals outside a palette file, and
selectors defined in two stylesheets under the same at-rule context. Stdlib only; read-only.

Deliberately approximate (advisory, never enforced):
- Colors are counted in declaration values only. Strings and url() are masked; rgb()/hsl()/oklch()
  calls built from var() are token compositions, not literals. SCSS `$name:` and LESS `@name:`
  definition lines are skipped, as is any file whose name says palette, tokens, theme or variables.
- Duplicate selectors compare rules whose ancestors are all context at-rules (@media, @supports,
  @container, @layer, @scope), and only selectors that name a class, id or attribute: element,
  universal and :root rules are each app's reset/base layer, and a repo holding several apps has one
  per app. Rules nested in other rules (SCSS/LESS/native nesting) and rules
  inside mixins, keyframes and other at-rules are not compared. Indented `.sass` has no braces, so
  it gets the color count only.
"""
import collections
import os
import re

PALETTE_NAME = re.compile(r"palette|tokens?|themes?|variables", re.IGNORECASE)
CONTEXT_AT_RULES = {"media", "supports", "container", "layer", "scope"}
NAMED_COLORS = set("""
aliceblue antiquewhite aqua aquamarine azure beige bisque black blanchedalmond blue blueviolet brown
burlywood cadetblue chartreuse chocolate coral cornflowerblue cornsilk crimson cyan darkblue darkcyan
darkgoldenrod darkgray darkgreen darkgrey darkkhaki darkmagenta darkolivegreen darkorange darkorchid
darkred darksalmon darkseagreen darkslateblue darkslategray darkslategrey darkturquoise darkviolet
deeppink deepskyblue dimgray dimgrey dodgerblue firebrick floralwhite forestgreen fuchsia gainsboro
ghostwhite gold goldenrod gray green greenyellow grey honeydew hotpink indianred indigo ivory khaki
lavender lavenderblush lawngreen lemonchiffon lightblue lightcoral lightcyan lightgoldenrodyellow
lightgray lightgreen lightgrey lightpink lightsalmon lightseagreen lightskyblue lightslategray
lightslategrey lightsteelblue lightyellow lime limegreen linen magenta maroon mediumaquamarine
mediumblue mediumorchid mediumpurple mediumseagreen mediumslateblue mediumspringgreen mediumturquoise
mediumvioletred midnightblue mintcream mistyrose moccasin navajowhite navy oldlace olive olivedrab
orange orangered orchid palegoldenrod palegreen paleturquoise palevioletred papayawhip peachpuff peru
pink plum powderblue purple rebeccapurple red rosybrown royalblue saddlebrown salmon sandybrown
seagreen seashell sienna silver skyblue slateblue slategray slategrey snow springgreen steelblue tan
teal thistle tomato turquoise violet wheat white whitesmoke yellow yellowgreen
""".split())
HEX = re.compile(r"#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3,4})(?![\w-])")
COLOR_FN = re.compile(r"(?<![\w-])(?:rgba?|hsla?|hwb|lab|lch|oklab|oklch|color)\s*\(([^()]*(?:\([^()]*\)[^()]*)*)\)",
                      re.IGNORECASE)
IDENT = re.compile(r"[A-Za-z_-][\w-]*")
DECLARATION = re.compile(r"(?<![\w-])(-{0,2}[A-Za-z][\w-]*)\s*:\s*([^;{}]+)(?=[;}])")
COMPONENT_SELECTOR = re.compile(r"[.#\[]")
PREPROC_DEF = re.compile(r"^\s*[$@][\w-]+\s*:")
MASK = re.compile(r"\"(?:\\.|[^\"\\\n])*\"|'(?:\\.|[^'\\\n])*'|url\([^)]*\)", re.IGNORECASE)


def blank(m):
    return re.sub(r"[^\n]", " ", m.group(0))


def strip_comments(text, ext):
    text = re.sub(r"/\*.*?\*/", blank, text, flags=re.DOTALL)
    if ext in (".scss", ".sass", ".less"):
        text = re.sub(r"(^|[ \t])//[^\n]*", blank, text, flags=re.MULTILINE)
    return text


def is_palette(path):
    return bool(PALETTE_NAME.search(os.path.basename(path)))


def value_colors(value):
    masked = MASK.sub(blank, value)
    found = HEX.findall(masked)
    found += [m.group(0).split("(")[0] for m in COLOR_FN.finditer(masked) if "var(" not in m.group(1)]
    found += [w for w in IDENT.findall(COLOR_FN.sub(" ", HEX.sub(" ", masked))) if w.lower() in NAMED_COLORS]
    return found


def color_literals(text, ext):
    """[(line, literal)] for color literals in declaration values."""
    text = strip_comments(text, ext)
    lines = text.split("\n")
    keep = "\n".join("" if PREPROC_DEF.match(ln) else ln for ln in lines)
    if ext == ".sass":  # indented syntax: declarations end at the newline
        keep = re.sub(r"\n", ";\n", keep)
    out = []
    for m in DECLARATION.finditer(keep):
        line = keep.count("\n", 0, m.start(2)) + 1
        out += [(line, c) for c in value_colors(m.group(2))]
    return out


def rule_preludes(text):
    """Yield (context, prelude) for each rule whose ancestors are all context at-rules."""
    stack, buf, i, n = [], [], 0, len(text)
    while i < n:
        ch = text[i]
        if ch in "\"'":
            j = i + 1
            while j < n and text[j] != ch and text[j] != "\n":
                j += 2 if text[j] == "\\" else 1
            buf.append(text[i:j + 1])
            i = j + 1
            continue
        if ch in "#@" and text[i + 1:i + 2] == "{":  # SCSS #{...} / LESS @{...} interpolation
            j = text.find("}", i)
            j = n if j < 0 else j
            buf.append(text[i:j + 1])
            i = j + 1
            continue
        if ch == "{":
            prelude = " ".join("".join(buf).split())
            if prelude.startswith("@"):
                name = re.match(r"@([\w-]+)", prelude)
                kind = "context" if name and name.group(1).lower() in CONTEXT_AT_RULES else "other"
            else:
                kind = "rule"
            if kind == "rule" and all(k == "context" for k, _ in stack):
                yield tuple(p for _, p in stack), prelude
            stack.append((kind, prelude))
            buf = []
        elif ch == "}":
            if stack:
                stack.pop()
            buf = []
        elif ch == ";":
            buf = []
        else:
            buf.append(ch)
        i += 1


def split_selectors(prelude):
    parts, depth, cur = [], 0, []
    for ch in prelude:
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    parts.append("".join(cur))
    return [re.sub(r"\s*([>+~])\s*", r"\1", " ".join(p.split())) for p in parts if p.strip()]


def collect(root, paths):
    """Advisory stylesheet metrics for the given repo-relative stylesheet paths."""
    colors, palettes, owners = {}, [], collections.defaultdict(set)
    for path in sorted(paths):
        ext = os.path.splitext(path)[1]
        try:
            with open(os.path.join(root, path), encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError:
            continue
        if is_palette(path):
            palettes.append(path)
        else:
            found = color_literals(text, ext)
            if found:
                colors[path] = {"count": len(found), "first": [f"{ln}:{c}" for ln, c in found[:3]]}
        if ext != ".sass":
            for context, prelude in rule_preludes(strip_comments(text, ext)):
                for sel in split_selectors(prelude):
                    if not COMPONENT_SELECTOR.search(sel):
                        continue
                    owners[(" / ".join(context), sel)].add(path)
    dupes = [{"context": c, "selector": s, "files": sorted(f)} for (c, s), f in owners.items() if len(f) > 1]
    dupes.sort(key=lambda d: (-len(d["files"]), d["context"], d["selector"]))
    return {"color_literals": colors, "palette_files": palettes, "duplicate_selectors": dupes}
