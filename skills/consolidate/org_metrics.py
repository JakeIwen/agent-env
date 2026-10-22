"""Advisory organization metrics for drift_check.py `check` only (never `ratchet`, never `rebaseline`):
stylesheet color literals and duplicate selectors (css_metrics), import cycles and grab-bag modules
(import_graph), and co-change coupling (cochange). Nothing here fails a run; a metric that errors is
reported as skipped. Stdlib only; never imports or executes project code.
"""
import cochange
import css_metrics
import import_graph


def collect(root, cur, style_ext):
    """cur: drift_check.measure() output; its files are the measured, non-excluded source paths.
    style_ext: drift_check.STYLE_EXT (declared once there)."""
    paths, tests = sorted(cur["files"]), set(cur["tests"])
    out, skipped = {}, {}
    steps = (
        ("stylesheets", lambda: css_metrics.collect(root, [p for p in paths if p.endswith(tuple(style_ext))])),
        ("imports", lambda: import_graph.collect(root, paths, tests)),
        ("cochange", lambda: cochange.collect(root, paths, tests)),
    )
    for name, run in steps:
        try:
            out[name] = run()
        except Exception as e:  # advisory: one broken metric must not hide the others or fail `check`
            skipped[name] = f"{e.__class__.__name__}: {e}"
    out["skipped"] = skipped
    return out


def print_report(org):
    css, imp, co = org.get("stylesheets"), org.get("imports"), org.get("cochange")
    if css is not None:
        colors = css["color_literals"]
        total = sum(v["count"] for v in colors.values())
        print(f"\nadvisory, color literals outside palette/tokens/theme/variables stylesheets: {total} in "
              f"{len(colors)} file(s) (top 5; palette files: {len(css['palette_files'])})")
        for p, v in sorted(colors.items(), key=lambda kv: -kv[1]["count"])[:5]:
            print(f"  {v['count']:6}  {p}  e.g. {', '.join(v['first'])}")
        dupes = css["duplicate_selectors"]
        print(f"advisory, selectors defined in 2+ stylesheets under the same at-rule context: {len(dupes)} (top 5)")
        for d in dupes[:5]:
            where = f" in {d['context']}" if d["context"] else ""
            print(f"  {len(d['files']):3}x  {d['selector']}{where}: {', '.join(d['files'][:3])}")
    if imp is not None:
        for key, label in (("python_cycles", "Python"), ("js_cycles", "JS/TS (relative imports)")):
            print(f"advisory, {label} import cycles: {len(imp[key])} (top 3)")
            for comp in imp[key][:3]:
                print(f"  {len(comp):3} modules: {', '.join(comp[:4])}{', ...' if len(comp) > 4 else ''}")
        print(f"advisory, grab-bag modules (named imports split into disjoint importer groups): "
              f"{len(imp['grab_bags'])} (top 3)")
        for g in imp["grab_bags"][:3]:
            groups = " | ".join(f"{{{', '.join(x['names'][:3])}}} by {len(x['importers'])}" for x in g["groups"][:4])
            print(f"  {len(g['groups']):3} groups  {g['module']}: {groups}")
    if co is not None:
        print(f"advisory, files in different top-level folders changed together {cochange.MIN_TOGETHER}+ times "
              f"(last {co['commits']} commits, {co['skipped_large']} with >{cochange.MAX_FILES} files skipped): "
              f"{len(co['pairs'])} (top 5)")
        for p in co["pairs"][:5]:
            print(f"  {p['together']:3}x  {p['a']} ({p['a_commits']}) + {p['b']} ({p['b_commits']})")
    for name, why in org.get("skipped", {}).items():
        print(f"advisory, {name}: skipped ({why})")
