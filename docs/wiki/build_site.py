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
  --bg: #0b1020;
  --bg-elev: #121a30;
  --bg-soft: #18223c;
  --line: rgba(232, 184, 109, 0.18);
  --text: #e8edf7;
  --muted: #9aa8c3;
  --gold: #e8b86d;
  --gold-2: #f0d7a8;
  --mint: #7ee0c5;
  --danger: #ffb4a8;
  --warn-bg: rgba(232, 184, 109, 0.12);
  --note-bg: rgba(126, 224, 197, 0.10);
  --shadow: 0 18px 50px rgba(0, 0, 0, 0.35);
  --radius: 14px;
  --max: 1120px;
  --sans: "IBM Plex Sans", "Segoe UI", system-ui, sans-serif;
  --serif: "Source Serif 4", "Iowan Old Style", Georgia, serif;
  --mono: "IBM Plex Mono", ui-monospace, monospace;
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  margin: 0;
  min-height: 100vh;
  font-family: var(--sans);
  color: var(--text);
  background:
    radial-gradient(1200px 500px at 10% -10%, rgba(232, 184, 109, 0.14), transparent 55%),
    radial-gradient(900px 420px at 110% 0%, rgba(126, 224, 197, 0.10), transparent 50%),
    var(--bg);
  line-height: 1.65;
}
a { color: var(--gold-2); text-decoration-thickness: 1px; text-underline-offset: 3px; }
a:hover { color: var(--gold); }
.skip {
  position: absolute; left: -999px; top: 0;
}
.skip:focus { left: 1rem; top: 1rem; background: var(--bg-elev); padding: .5rem 1rem; z-index: 20; }
.topbar {
  position: sticky; top: 0; z-index: 10;
  backdrop-filter: blur(14px);
  background: rgba(11, 16, 32, 0.78);
  border-bottom: 1px solid var(--line);
}
.topbar-inner {
  max-width: var(--max);
  margin: 0 auto;
  padding: 0.85rem 1.25rem;
  display: flex; align-items: center; gap: 1rem; justify-content: space-between;
}
.brand { display: flex; flex-direction: column; gap: 0.15rem; text-decoration: none; color: inherit; }
.brand strong {
  font-family: var(--serif);
  font-size: 1.15rem;
  letter-spacing: -0.02em;
  color: var(--gold-2);
}
.brand span { font-size: 0.78rem; color: var(--muted); }
.top-actions { display: flex; align-items: center; gap: 0.7rem; }
.badge {
  font-family: var(--mono);
  font-size: 0.75rem;
  padding: 0.2rem 0.55rem;
  border-radius: 999px;
  border: 1px solid var(--line);
  color: var(--mint);
}
.btn {
  display: inline-flex; align-items: center; gap: 0.35rem;
  border: 1px solid var(--line);
  background: var(--bg-soft);
  color: var(--text);
  padding: 0.4rem 0.75rem;
  border-radius: 999px;
  text-decoration: none;
  font-size: 0.88rem;
}
.btn:hover { border-color: var(--gold); color: var(--gold-2); }
.nav-toggle {
  display: none;
  background: var(--bg-soft);
  border: 1px solid var(--line);
  color: var(--text);
  border-radius: 8px;
  padding: 0.35rem 0.6rem;
}
.shell {
  max-width: var(--max);
  margin: 0 auto;
  padding: 1.4rem 1.25rem 3rem;
  display: grid;
  grid-template-columns: 240px minmax(0, 1fr);
  gap: 1.5rem;
}
nav.side {
  position: sticky; top: 4.6rem; align-self: start;
  background: var(--bg-elev);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 1rem 0.85rem;
  box-shadow: var(--shadow);
}
nav.side h2 {
  margin: 0 0 0.6rem;
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: var(--muted);
  font-weight: 600;
}
nav.side ol { list-style: none; margin: 0; padding: 0; }
nav.side li { margin: 0.15rem 0; }
nav.side a {
  display: block;
  text-decoration: none;
  color: var(--text);
  padding: 0.38rem 0.55rem;
  border-radius: 8px;
  font-size: 0.92rem;
}
nav.side a:hover, nav.side a[aria-current="page"] {
  background: rgba(232, 184, 109, 0.12);
  color: var(--gold-2);
}
main.page {
  background: var(--bg-elev);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 1.6rem 1.7rem 2.2rem;
  box-shadow: var(--shadow);
  min-width: 0;
}
main.page > h1:first-child { margin-top: 0; }
h1, h2, h3, h4 {
  font-family: var(--serif);
  line-height: 1.25;
  letter-spacing: -0.02em;
  font-weight: 600;
}
h1 { font-size: clamp(1.7rem, 3vw, 2.15rem); margin-bottom: 0.8rem; }
h2 { margin-top: 1.8rem; padding-top: 0.4rem; border-top: 1px solid var(--line); font-size: 1.35rem; }
h3 { font-size: 1.12rem; }
p, li { color: var(--text); }
.muted, main.page > p:first-of-type { color: var(--muted); }
table {
  width: 100%;
  border-collapse: collapse;
  margin: 1rem 0 1.3rem;
  font-size: 0.94rem;
  overflow-x: auto;
  display: block;
}
th, td {
  border: 1px solid var(--line);
  padding: 0.5rem 0.7rem;
  text-align: left;
  vertical-align: top;
}
th { background: var(--bg-soft); color: var(--gold-2); font-weight: 600; }
tr:nth-child(even) td { background: rgba(255,255,255,0.02); }
code, pre { font-family: var(--mono); font-size: 0.86em; }
:not(pre) > code {
  background: var(--bg-soft);
  padding: 0.12em 0.38em;
  border-radius: 5px;
  color: var(--mint);
}
pre {
  background: #080d1a;
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 0.95rem 1rem;
  overflow-x: auto;
}
pre code { color: #d7e3ff; background: none; padding: 0; }
blockquote {
  margin: 1rem 0;
  padding: 0.2rem 0 0.2rem 1rem;
  border-left: 3px solid var(--gold);
  color: var(--muted);
}
.callout {
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 0.75rem 1rem;
  margin: 1.1rem 0;
  background: var(--note-bg);
}
.callout-warning, .callout-caution { background: var(--warn-bg); }
.callout-label {
  margin: 0 0 0.35rem;
  font-size: 0.78rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--gold);
  font-weight: 700;
}
hr { border: 0; border-top: 1px solid var(--line); margin: 1.6rem 0; }
.katex-display { overflow-x: auto; overflow-y: hidden; }
footer.site {
  max-width: var(--max);
  margin: 0 auto 2rem;
  padding: 0 1.25rem;
  color: var(--muted);
  font-size: 0.88rem;
}
@media (max-width: 860px) {
  .nav-toggle { display: inline-block; }
  .shell { grid-template-columns: 1fr; }
  nav.side { position: static; display: none; }
  nav.side.open { display: block; }
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
) -> str:
    nav_items = []
    for label, href in nav:
        cur = ' aria-current="page"' if href == current else ""
        nav_items.append(f'        <li><a href="{html.escape(href)}"{cur}>{html.escape(label)}</a></li>')
    nav_s = "\n".join(nav_items)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>{html.escape(title)} · Best Prime</title>
  <meta name="description" content="Deterministic primality testing wiki — no stochastic Miller–Rabin."/>
  <link rel="preconnect" href="https://fonts.googleapis.com"/>
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/>
  <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600&family=Source+Serif+4:opsz,wght@8..60,500;8..60,600&display=swap" rel="stylesheet"/>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css"/>
  <style>{CSS}</style>
</head>
<body>
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
        html_out = page_html(
            title=page_title,
            body=body,
            nav=nav,
            current=current,
            version=version,
            footer_html=footer_html,
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
