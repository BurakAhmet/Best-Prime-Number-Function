#!/usr/bin/env python3
"""Compile docs/wiki Markdown into a static HTML site for GitHub Pages.

Renders GFM-ish Markdown (tables, fences, GitHub alerts, $math$) instead of
dumping raw source into <pre>. Nav comes from _Sidebar.md.
"""
from __future__ import annotations

import html
import re
import shutil
import sys
from pathlib import Path

try:
    import markdown
except ImportError:  # pragma: no cover
    print(
        "Missing dependency: pip install markdown\n"
        "(CI: Publish wiki workflow installs it before this script.)",
        file=sys.stderr,
    )
    raise SystemExit(2)

ROOT = Path(__file__).resolve().parents[2]
WIKI = Path(__file__).resolve().parent
MD_EXT = [
    "extra",
    "sane_lists",
    "smarty",
    "toc",
]

ALERT_RE = re.compile(
    r"^> \[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\][^\n]*\n((?:^>.*\n?)*)",
    re.MULTILINE,
)
WIKI_LINK_RE = re.compile(
    r"\[([^\]]+)\]\((Home|Project-restrictions|Algorithm-overview|"
    r"CI-and-automation|Agent-briefing|Contributing|Benchmarks|Hall-of-fame)"
    r"((?:\.md)?)(#[^)]*)?\)"
)
NAV_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")

ALERT_META = {
    "NOTE": ("Note", "note"),
    "TIP": ("Tip", "tip"),
    "IMPORTANT": ("Important", "important"),
    "WARNING": ("Warning", "warning"),
    "CAUTION": ("Caution", "caution"),
}

NAV_FALLBACK = [
    ("Home", "index.html"),
    ("Project restrictions", "Project-restrictions.html"),
    ("Algorithm overview", "Algorithm-overview.html"),
    ("Algorithm history", "Algorithm-history.html"),
    ("CI and automation", "CI-and-automation.html"),
    ("Agent briefing", "Agent-briefing.html"),
    ("Contributing", "Contributing.html"),
    ("Benchmarks", "Benchmarks.html"),
    ("Hall of fame", "Hall-of-fame.html"),
]


def package_version() -> str:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    m = re.search(r'^version\s*=\s*"([^"]+)"', text, re.M)
    return m.group(1) if m else "dev"


def preprocess(md: str) -> str:
    def alert(m: re.Match[str]) -> str:
        title, kind = ALERT_META.get(m.group(1).upper(), (m.group(1).title(), "note"))
        inner = re.sub(r"^> ?", "", m.group(2), flags=re.M).strip()
        inner_html = markdown.markdown(inner, extensions=["extra", "sane_lists", "smarty"])
        return (
            f'\n\n<div class="callout callout-{kind}" role="note">'
            f'<p class="callout-label">{html.escape(title)}</p>'
            f"{inner_html}</div>\n\n"
        )

    md = ALERT_RE.sub(alert, md)
    md = WIKI_LINK_RE.sub(
        lambda m: f"[{m.group(1)}]({_wiki_href(m.group(2))}{m.group(4) or ''})",
        md,
    )
    md = md.replace(
        "https://github.com/BurakAhmet/Best-Prime-Number-Function/blob/main/docs/ALGORITHM_HISTORY.md",
        "Algorithm-history.html",
    )
    return md


def _wiki_href(stem: str) -> str:
    return "index.html" if stem == "Home" else f"{stem}.html"


def parse_nav(sidebar: Path, stems: set[str]) -> list[tuple[str, str]]:
    if not sidebar.is_file():
        return list(NAV_FALLBACK)
    items: list[tuple[str, str]] = []
    seen: set[str] = set()
    for raw in sidebar.read_text(encoding="utf-8").splitlines():
        m = NAV_LINK_RE.search(raw)
        if not m:
            continue
        label, href = m.group(1), m.group(2)
        label = label.replace("**", "").strip()
        if href.startswith("http"):
            if "ALGORITHM_HISTORY" in href:
                href = "Algorithm-history.html"
            else:
                continue
        else:
            stem = Path(href.replace(".md", "")).name
            if stem == "Home":
                href = "index.html"
            elif stem in stems or stem == "Algorithm-history":
                href = f"{stem}.html"
            else:
                continue
        if href in seen:
            continue
        seen.add(href)
        items.append((label, href))
    return items or list(NAV_FALLBACK)


def render_md(text: str) -> str:
    conv = markdown.Markdown(extensions=MD_EXT, output_format="html5")
    return conv.convert(preprocess(text))


def rewrite_html_hrefs(body: str, stems: set[str]) -> str:
    def repl(m: re.Match[str]) -> str:
        href = m.group(1)
        if href.startswith(("http://", "https://", "#", "mailto:", "data:")):
            return m.group(0)
        path, frag = href, ""
        if "#" in href:
            path, frag = href.split("#", 1)
            frag = "#" + frag
        stem = Path(path.replace(".md", "")).name
        if stem in {"Home", "index", ""}:
            return f'href="index.html{frag}"'
        if stem in stems:
            return f'href="{stem}.html{frag}"'
        return m.group(0)

    return re.sub(r'href="([^"]+)"', repl, body)


CSS = r"""
:root {
  --paper: #f4efe6;
  --sheet: #fffaf3;
  --ink: #1c1915;
  --muted: #6f675c;
  --line: #e2d8c8;
  --accent: #c23b22;
  --forest: #2f4a38;
  --soft: #efe6d6;
  --max: 1180px;
  --sans: "Figtree", "Segoe UI", system-ui, sans-serif;
  --serif: "Fraunces", "Iowan Old Style", Georgia, serif;
  --mono: "IBM Plex Mono", ui-monospace, monospace;
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  margin: 0;
  min-height: 100vh;
  font-family: var(--sans);
  color: var(--ink);
  background-color: var(--paper);
  background-image:
    radial-gradient(ellipse 80% 50% at 100% -10%, rgba(194, 59, 34, 0.08), transparent 50%),
    radial-gradient(circle at 8% 90%, rgba(47, 74, 56, 0.06), transparent 36%);
  line-height: 1.7;
}
body::before {
  content: "";
  pointer-events: none;
  position: fixed;
  inset: 0;
  opacity: 0.22;
  background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='140' height='140'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='2' stitchTiles='stitch'/><feColorMatrix values='0 0 0 0 0.15  0 0 0 0 0.12  0 0 0 0 0.08  0 0 0 0.25 0'/></filter><rect width='100%' height='100%' filter='url(%23n)'/></svg>");
  z-index: 0;
}
a { color: var(--accent); text-decoration-thickness: 1px; text-underline-offset: 3px; }
a:hover { color: var(--ink); }
.skip { position: absolute; left: -999px; top: 0; }
.skip:focus { left: 1rem; top: 1rem; background: var(--sheet); padding: .5rem 1rem; z-index: 20; }
.topbar {
  position: sticky; top: 0; z-index: 10;
  background: rgba(244, 239, 230, 0.86);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--line);
}
.topbar-inner {
  max-width: var(--max);
  margin: 0 auto;
  padding: 1rem 1.4rem;
  display: flex; align-items: baseline; justify-content: space-between; gap: 1rem;
}
.brand { text-decoration: none; color: inherit; display: flex; flex-direction: column; gap: 0.1rem; }
.brand strong {
  font-family: var(--serif);
  font-weight: 500;
  font-size: 1.35rem;
  letter-spacing: -0.03em;
  font-style: italic;
}
.brand span { font-size: 0.75rem; color: var(--muted); letter-spacing: 0.08em; text-transform: uppercase; }
.top-actions { display: flex; align-items: center; gap: 0.7rem; }
.badge {
  font-family: var(--mono);
  font-size: 0.72rem;
  letter-spacing: 0.06em;
  color: var(--forest);
}
.btn {
  display: inline-flex;
  border: 1px solid var(--ink);
  color: var(--ink);
  text-decoration: none;
  padding: 0.38rem 0.8rem;
  border-radius: 999px;
  font-size: 0.8rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
.btn:hover { background: var(--ink); color: var(--paper); }
.nav-toggle {
  display: none;
  background: transparent;
  border: 1px solid var(--ink);
  color: var(--ink);
  border-radius: 999px;
  padding: 0.35rem 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-size: 0.78rem;
}
.shell {
  position: relative;
  z-index: 1;
  max-width: var(--max);
  margin: 0 auto;
  padding: 2rem 1.4rem 3.5rem;
  display: grid;
  grid-template-columns: 220px minmax(0, 1fr);
  gap: 2.4rem;
}
nav.side { position: sticky; top: 5.2rem; align-self: start; padding-top: 0.2rem; }
nav.side h2 {
  margin: 0 0 0.85rem;
  font-family: var(--sans);
  font-size: 0.7rem;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--muted);
  font-weight: 600;
  border: 0;
  padding: 0;
}
nav.side ol { list-style: none; margin: 0; padding: 0; }
nav.side li + li { margin-top: 0.15rem; }
nav.side a {
  display: flex; align-items: baseline; gap: 0.65rem;
  text-decoration: none;
  color: var(--ink);
  padding: 0.32rem 0;
  font-size: 0.95rem;
  border-bottom: 1px solid transparent;
}
nav.side .idx {
  font-family: var(--mono);
  font-size: 0.68rem;
  color: var(--muted);
  min-width: 1.4rem;
}
nav.side a:hover, nav.side a[aria-current="page"] { color: var(--accent); }
nav.side a[aria-current="page"] .idx { color: var(--accent); }
main.page {
  background: var(--sheet);
  border: 1px solid var(--line);
  padding: 2.2rem 2.3rem 2.8rem;
  min-width: 0;
  box-shadow: 0 24px 60px rgba(28, 25, 21, 0.06);
}
.is-home main.page > h1:first-child {
  font-size: clamp(2.4rem, 6vw, 3.7rem);
  line-height: 1.02;
  max-width: 13ch;
  font-weight: 500;
  font-style: italic;
  letter-spacing: -0.04em;
  margin: 0 0 1rem;
}
main.page > h1:first-child { margin-top: 0; }
h1, h2, h3, h4 {
  font-family: var(--serif);
  line-height: 1.22;
  letter-spacing: -0.03em;
  font-weight: 550;
}
h1 { font-size: clamp(1.85rem, 3.4vw, 2.4rem); margin-bottom: 0.85rem; }
h2 {
  margin-top: 2.1rem;
  padding-top: 0;
  border-top: none;
  font-size: 1.45rem;
  font-style: italic;
}
h3 { font-size: 1.12rem; }
p, li { color: var(--ink); }
main.page > p:first-of-type {
  color: var(--muted);
  font-size: 1.08rem;
  max-width: 42rem;
}
table {
  width: 100%;
  border-collapse: collapse;
  margin: 1.1rem 0 1.4rem;
  font-size: 0.94rem;
  display: block;
  overflow-x: auto;
}
th, td {
  border: 0;
  border-bottom: 1px solid var(--line);
  padding: 0.62rem 0.55rem 0.62rem 0;
  text-align: left;
  vertical-align: top;
}
th {
  background: transparent;
  color: var(--muted);
  font-weight: 600;
  font-size: 0.75rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
code, pre { font-family: var(--mono); font-size: 0.86em; }
:not(pre) > code {
  background: var(--soft);
  padding: 0.1em 0.35em;
  border-radius: 4px;
  color: var(--forest);
}
pre {
  background: #231f1a;
  color: #f4efe6;
  border: 0;
  border-radius: 2px;
  padding: 1.05rem 1.1rem;
  overflow-x: auto;
}
pre code { color: inherit; background: none; padding: 0; }
blockquote {
  margin: 1rem 0;
  padding: 0.15rem 0 0.15rem 1rem;
  border-left: 2px solid var(--accent);
  color: var(--muted);
}
.callout {
  border: 0;
  border-left: 2px solid var(--accent);
  border-radius: 0;
  padding: 0.15rem 0 0.15rem 1rem;
  margin: 1.2rem 0;
  background: transparent;
}
.callout-warning, .callout-caution { background: transparent; }
.callout-label {
  margin: 0 0 0.25rem;
  font-size: 0.72rem;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--accent);
  font-weight: 700;
}
hr { border: 0; border-top: 1px solid var(--line); margin: 2rem 0; }
.katex-display { overflow-x: auto; overflow-y: hidden; }
footer.site {
  position: relative;
  z-index: 1;
  max-width: var(--max);
  margin: 0 auto 2.2rem;
  padding: 0 1.4rem;
  color: var(--muted);
  font-size: 0.86rem;
}
@media (max-width: 860px) {
  .nav-toggle { display: inline-block; }
  .shell { grid-template-columns: 1fr; padding-top: 1.2rem; gap: 1.2rem; }
  nav.side { position: static; display: none; }
  nav.side.open { display: block; }
  main.page { padding: 1.4rem 1.15rem 2rem; }
}
"""

def page_html(
    *,
    title: str,
    body: str,
    nav: list[tuple[str, str]],
    current: str,
    version: str,
    footer_html: str,
    extra_head: str = "",
    extra_scripts: str = "",
) -> str:
    nav_items = []
    for i, (label, href) in enumerate(nav, 1):
        cur = ' aria-current="page"' if href == current else ""
        nav_items.append(
            f'        <li><a href="{html.escape(href)}"{cur}>'
            f'<span class="idx">{i:02d}</span>{html.escape(label)}</a></li>'
        )
    nav_s = "\n".join(nav_items)
    body_cls = ' class="is-home"' if current == "index.html" else ""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>{html.escape(title)} · Best Prime</title>
  <meta name="description" content="Deterministic primality testing wiki — no stochastic Miller–Rabin."/>
  <link rel="preconnect" href="https://fonts.googleapis.com"/>
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/>
  <link href="https://fonts.googleapis.com/css2?family=Figtree:wght@400;500;600;700&family=Fraunces:ital,opsz,wght@0,9..144,500;0,9..144,600;1,9..144,500;1,9..144,600&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet"/>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css"/>
  {extra_head}
  <style>{CSS}</style>
</head>
<body{body_cls}>
  <a class="skip" href="#content">Skip to content</a>
  <header class="topbar">
    <div class="topbar-inner">
      <a class="brand" href="index.html">
        <strong>Best Prime</strong>
        <span>Fully deterministic primality</span>
      </a>
      <div class="top-actions">
        <span class="badge">v{html.escape(version)}</span>
        <button class="nav-toggle" type="button" onclick="document.getElementById('sidenav').classList.toggle('open')">Menu</button>
        <a class="btn" href="https://github.com/BurakAhmet/Best-Prime-Number-Function">GitHub</a>
      </div>
    </div>
  </header>
  <div class="shell">
    <nav class="side" id="sidenav" aria-label="Wiki">
      <h2>Wiki</h2>
      <ol>
{nav_s}
      </ol>
    </nav>
    <main class="page" id="content">
{body}
    </main>
  </div>
  <footer class="site">{footer_html}</footer>
  <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js"></script>
  <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js"
    onload="renderMathInElement(document.getElementById('content'), {{
      delimiters: [
        {{left: '$$', right: '$$', display: true}},
        {{left: '$', right: '$', display: false}}
      ],
      throwOnError: false
    }});"></script>
  {extra_scripts}
</body>
</html>
"""


def collect_sources() -> list[tuple[str, Path, str]]:
    """Return (stem, path, title) pages to publish."""
    pages: list[tuple[str, Path, str]] = []
    for p in sorted(WIKI.glob("*.md")):
        if p.name.startswith("_"):
            continue
        stem = p.stem
        title = stem.replace("-", " ")
        pages.append((stem, p, title))
    hist = ROOT / "docs" / "ALGORITHM_HISTORY.md"
    if hist.is_file():
        pages.append(("Algorithm-history", hist, "Algorithm history"))
    return pages


def main() -> int:
    dest = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("_site")
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    assets = WIKI / "assets"
    if assets.is_dir():
        shutil.copytree(assets, dest / "assets")

    version = package_version()
    sources = collect_sources()
    stems = {s for s, _, _ in sources} | {"Home", "index"}
    nav = parse_nav(WIKI / "_Sidebar.md", stems)
    footer_src = (WIKI / "_Footer.md").read_text(encoding="utf-8") if (WIKI / "_Footer.md").is_file() else ""
    footer_html = render_md(footer_src) if footer_src.strip() else (
        '<p>Deterministic primality · no stochastic Miller–Rabin · '
        '<a href="https://github.com/BurakAhmet/Best-Prime-Number-Function">source</a></p>'
    )

    built = 0
    for stem, path, title in sources:
        body = rewrite_html_hrefs(render_md(path.read_text(encoding="utf-8")), stems)
        current = "index.html" if stem == "Home" else f"{stem}.html"
        page_title = "Home" if stem == "Home" else title
        is_home = stem == "Home"
        html_out = page_html(
            title=page_title,
            body=body,
            nav=nav,
            current=current,
            version=version,
            footer_html=footer_html,
            extra_head='  <link rel="stylesheet" href="assets/checker.css"/>\n' if is_home else "",
            extra_scripts='  <script src="assets/checker.js" defer></script>\n' if is_home else "",
        )
        out_name = "index.html" if stem == "Home" else f"{stem}.html"
        (dest / out_name).write_text(html_out, encoding="utf-8")
        if stem == "Home":
            (dest / "Home.html").write_text(html_out, encoding="utf-8")
        built += 1

    (dest / ".nojekyll").write_text("", encoding="utf-8")
    print(f"Built {built} markdown pages (+ Home.html alias) into {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
