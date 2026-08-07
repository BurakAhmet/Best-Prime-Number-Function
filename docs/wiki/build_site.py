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
  --board: #163028;
  --chalk: #e9f2ea;
  --chalk-dim: #9db5a6;
  --chalk-yellow: #f3e08a;
  --sheet: #fbf6ea;
  --ink: #1b2437;
  --muted: #5c6778;
  --line: #e4d9c4;
  --accent: #c45c2c;
  --forest: #245c3d;
  --soft: #efe4cf;
  --max: 1180px;
  --sans: "Source Sans 3", "Segoe UI", system-ui, sans-serif;
  --serif: "STIX Two Text", "Times New Roman", serif;
  --mono: "JetBrains Mono", ui-monospace, monospace;
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  margin: 0;
  min-height: 100vh;
  font-family: var(--sans);
  color: var(--chalk);
  background-color: var(--board);
  background-image:
    linear-gradient(rgba(233, 242, 234, 0.045) 1px, transparent 1px),
    linear-gradient(90deg, rgba(233, 242, 234, 0.045) 1px, transparent 1px);
  background-size: 28px 28px;
  line-height: 1.7;
}
a { color: var(--chalk-yellow); text-underline-offset: 3px; }
a:hover { color: #fff; }
main.page a { color: var(--accent); }
main.page a:hover { color: var(--ink); }
.skip { position: absolute; left: -999px; top: 0; }
.skip:focus { left: 1rem; top: 1rem; background: var(--sheet); color: var(--ink); padding: .5rem 1rem; z-index: 20; }
.topbar {
  position: sticky; top: 0; z-index: 10;
  background: rgba(22, 48, 40, 0.92);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid rgba(233, 242, 234, 0.12);
}
.topbar-inner {
  max-width: var(--max);
  margin: 0 auto;
  padding: 0.95rem 1.4rem;
  display: flex; align-items: baseline; justify-content: space-between; gap: 1rem;
}
.brand { text-decoration: none; color: inherit; display: flex; flex-direction: column; gap: 0.12rem; }
.brand strong {
  font-family: var(--serif);
  font-weight: 600;
  font-size: 1.4rem;
  letter-spacing: -0.02em;
  color: var(--chalk);
}
.brand span { font-size: 0.74rem; color: var(--chalk-dim); letter-spacing: 0.04em; }
.top-actions { display: flex; align-items: center; gap: 0.7rem; }
.badge {
  font-family: var(--mono);
  font-size: 0.72rem;
  color: var(--chalk-yellow);
}
.btn {
  display: inline-flex;
  border: 1px solid rgba(233, 242, 234, 0.35);
  color: var(--chalk);
  text-decoration: none;
  padding: 0.36rem 0.8rem;
  border-radius: 2px;
  font-size: 0.8rem;
}
.btn:hover { background: var(--chalk-yellow); color: var(--board); border-color: var(--chalk-yellow); }
.nav-toggle {
  display: none;
  background: transparent;
  border: 1px solid rgba(233, 242, 234, 0.35);
  color: var(--chalk);
  border-radius: 2px;
  padding: 0.35rem 0.7rem;
  font-size: 0.8rem;
}
.shell {
  max-width: var(--max);
  margin: 0 auto;
  padding: 1.8rem 1.4rem 3.2rem;
  display: grid;
  grid-template-columns: 220px minmax(0, 1fr);
  gap: 1.8rem;
}
nav.side { position: sticky; top: 5rem; align-self: start; }
nav.side h2 {
  margin: 0 0 0.75rem;
  font-family: var(--sans);
  font-size: 0.7rem;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--chalk-dim);
  font-weight: 600;
  border: 0;
  padding: 0;
}
nav.side ol { list-style: none; margin: 0; padding: 0; }
nav.side a {
  display: flex; align-items: baseline; gap: 0.6rem;
  text-decoration: none;
  color: var(--chalk);
  padding: 0.3rem 0;
  font-size: 0.94rem;
}
nav.side .idx { font-family: var(--mono); font-size: 0.68rem; color: var(--chalk-dim); min-width: 1.4rem; }
nav.side a:hover, nav.side a[aria-current="page"] { color: var(--chalk-yellow); }
nav.side a[aria-current="page"] .idx { color: var(--chalk-yellow); }
main.page {
  background: var(--sheet);
  color: var(--ink);
  border: 1px solid rgba(0,0,0,0.06);
  padding: 2.1rem 2.25rem 2.6rem;
  min-width: 0;
  box-shadow: 0 18px 50px rgba(0, 0, 0, 0.18);
}
main.page, main.page p, main.page li { color: var(--ink); }
.is-home main.page > h1:first-child {
  font-size: clamp(2.2rem, 5vw, 3.2rem);
  line-height: 1.08;
  max-width: 16ch;
  font-weight: 600;
  margin: 0 0 0.9rem;
}
main.page > h1:first-child { margin-top: 0; }
h1, h2, h3, h4 {
  font-family: var(--serif);
  line-height: 1.25;
  font-weight: 600;
}
h1 { font-size: clamp(1.75rem, 3vw, 2.25rem); margin-bottom: 0.8rem; }
h2 {
  margin-top: 1.9rem;
  border: 0;
  padding: 0;
  font-size: 1.35rem;
}
h2::before {
  content: "§ ";
  color: var(--accent);
  font-weight: 500;
}
h3 { font-size: 1.12rem; }
main.page > p:first-of-type {
  color: var(--muted);
  font-size: 1.06rem;
  max-width: 44rem;
}
table {
  width: 100%;
  border-collapse: collapse;
  margin: 1rem 0 1.35rem;
  font-size: 0.94rem;
  display: block;
  overflow-x: auto;
}
th, td {
  border: 0;
  border-bottom: 1px solid var(--line);
  padding: 0.58rem 0.5rem 0.58rem 0;
  text-align: left;
  vertical-align: top;
}
th {
  color: var(--muted);
  font-size: 0.74rem;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}
code, pre { font-family: var(--mono); font-size: 0.86em; }
:not(pre) > code {
  background: var(--soft);
  padding: 0.1em 0.34em;
  color: var(--forest);
}
pre {
  background: #12241d;
  color: #e9f2ea;
  border-radius: 2px;
  padding: 1rem 1.05rem;
  overflow-x: auto;
}
pre code { color: inherit; background: none; padding: 0; }
blockquote {
  margin: 1rem 0;
  padding-left: 1rem;
  border-left: 2px solid var(--accent);
  color: var(--muted);
}
.callout {
  border: 0;
  border-left: 2px solid var(--accent);
  padding: 0.1rem 0 0.1rem 1rem;
  margin: 1.15rem 0;
}
.callout-label {
  margin: 0 0 0.25rem;
  font-size: 0.72rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--accent);
  font-weight: 700;
}
hr { border: 0; border-top: 1px solid var(--line); margin: 1.8rem 0; }
.katex-display { overflow-x: auto; overflow-y: hidden; }
footer.site {
  max-width: var(--max);
  margin: 0 auto 2rem;
  padding: 0 1.4rem;
  color: var(--chalk-dim);
  font-size: 0.86rem;
}
footer.site a { color: var(--chalk-yellow); }
@media (max-width: 860px) {
  .nav-toggle { display: inline-block; }
  .shell { grid-template-columns: 1fr; padding-top: 1.1rem; }
  nav.side { position: static; display: none; }
  nav.side.open { display: block; }
  main.page { padding: 1.35rem 1.1rem 2rem; }
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
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500&family=STIX+Two+Text:ital,wght@0,400;0,600;1,400;1,600&family=Source+Sans+3:wght@400;600;700&display=swap" rel="stylesheet"/>
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
