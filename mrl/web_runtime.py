from __future__ import annotations

from dataclasses import dataclass
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Iterable

from config import DEFAULT_WEB_HOST, DEFAULT_WEB_PORT, DEFAULT_WEB_ROOT

FLASK_IMPORT_ERROR: Exception | None = None

try:  # pragma: no cover - optional dependency
    from flask import Flask, render_template_string

    FLASK_AVAILABLE = True
except Exception as exc:  # pragma: no cover - optional dependency
    Flask = None
    render_template_string = None
    FLASK_AVAILABLE = False
    FLASK_IMPORT_ERROR = exc

FLASK_INSTALL_HINT = "pip install flask"


@dataclass(frozen=True, slots=True)
class PageDefinition:
    route: str
    title: str
    body_lines: list[str]
    source_path: Path

    def render_html(self, navigation: str) -> str:
        body_html = "".join(f"<p>{escape(line)}</p>" for line in self.body_lines)
        return f"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(self.title)}</title>
  <style>
    :root {{ color-scheme: light; }}
    body {{ margin: 0; font-family: 'Segoe UI', sans-serif; background: linear-gradient(180deg, #08101f, #121b31 60%, #1a2542); color: #f4fbff; }}
    .shell {{ max-width: 920px; margin: 0 auto; padding: 32px 20px 64px; }}
    .brand {{ font-size: 12px; letter-spacing: 0.22em; text-transform: uppercase; color: #7ee5ff; margin-bottom: 12px; }}
    nav a {{ color: #d8f8ff; margin-right: 16px; text-decoration: none; font-weight: 600; }}
    .panel {{ margin-top: 28px; padding: 28px; border-radius: 20px; background: rgba(255,255,255,0.08); box-shadow: 0 24px 80px rgba(0,0,0,0.28); backdrop-filter: blur(12px); }}
    h1 {{ margin: 0 0 16px; font-size: 42px; }}
    p {{ font-size: 18px; line-height: 1.7; color: #e8f3ff; }}
  </style>
</head>
<body>
  <div class="shell">
    <div class="brand">MRL Web Runtime</div>
    <nav>{navigation}</nav>
    <div class="panel">
      <h1>{escape(self.title)}</h1>
      {body_html}
    </div>
  </div>
</body>
</html>
"""


@dataclass(frozen=True, slots=True)
class SiteDefinition:
    root: Path
    pages: dict[str, PageDefinition]

    def navigation_html(self) -> str:
        links = []
        for route, page in sorted(self.pages.items(), key=lambda item: item[0]):
            label = "home" if route == "/" else route.strip("/") or page.title.lower()
            links.append(f'<a href="{escape(route)}">{escape(label)}</a>')
        return "".join(links)


class WebRuntimeError(Exception):
    pass


def print_runtime_banner(site: SiteDefinition, *, mode: str, host: str, port: int) -> None:
    url = f"http://{host}:{port}"
    print(f"[web] Loaded {len(site.pages)} page(s) from {site.root}")

    if mode == "flask":
        print(f"[web] Flask runtime listening on {url}")
        return

    print(f"[web] Flask unavailable. Using built-in HTTP runtime on {url}")
    print("[web] Tip: install Flask to enable the Flask-backed runtime:")
    print(f"[web]   {FLASK_INSTALL_HINT}")
    if FLASK_IMPORT_ERROR is not None and not isinstance(FLASK_IMPORT_ERROR, ImportError):
        print(f"[web] Optional dependency error: {FLASK_IMPORT_ERROR}")


def load_site(root: str | Path | None = None) -> SiteDefinition:
    site_root = resolve_site_root(root)
    page_files = list(iter_page_files(site_root))
    if not page_files:
        raise WebRuntimeError(f"No .hi or .mrl pages found in {site_root}")

    pages = {page.route: page for page in (parse_page_file(path) for path in page_files)}
    return SiteDefinition(root=site_root, pages=pages)


def resolve_site_root(root: str | Path | None) -> Path:
    if root is None:
        default_root = Path.cwd() / DEFAULT_WEB_ROOT
        if default_root.exists():
            return default_root.resolve()
        return Path.cwd().resolve()
    return Path(root).resolve()


def iter_page_files(root: Path) -> Iterable[Path]:
    if root.is_file() and root.suffix in {".hi", ".mrl"}:
        yield root
        return

    if not root.exists():
        raise WebRuntimeError(f"Web root '{root}' does not exist.")

    for path in sorted(root.iterdir()):
        if path.is_file() and path.suffix in {".hi", ".mrl"}:
            yield path


def parse_page_file(path: Path) -> PageDefinition:
    route = "/" if path.stem == "home" else f"/{path.stem}"
    title = path.stem.replace("_", " ").title()
    body_lines: list[str] = []

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        if line.startswith("mrl "):
            line = line[4:].strip()

        if line.startswith("route "):
            route = normalize_route(unquote(line[6:].strip()))
            continue

        if line.startswith("title "):
            title = unquote(line[6:].strip())
            continue

        if line.startswith("bolo "):
            body_lines.append(unquote(line[5:].strip()))

    return PageDefinition(route=route, title=title, body_lines=body_lines, source_path=path)


def normalize_route(route: str) -> str:
    if not route:
        return "/"
    return route if route.startswith("/") else f"/{route}"


def unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def run_web_runtime(
    root: str | Path | None = None,
    *,
    host: str = DEFAULT_WEB_HOST,
    port: int = DEFAULT_WEB_PORT,
) -> None:
    site = load_site(root)
    try:
        if FLASK_AVAILABLE and Flask is not None and render_template_string is not None:
            app = build_flask_app(site)
            print_runtime_banner(site, mode="flask", host=host, port=port)
            app.run(host=host, port=port, debug=False)
            return

        print_runtime_banner(site, mode="builtin", host=host, port=port)
        run_builtin_server(site, host=host, port=port)
    except KeyboardInterrupt:  # pragma: no cover - runtime only
        print("\n[web] Runtime stopped.")


def run_web(
    root: str | Path | None = None,
    *,
    host: str = DEFAULT_WEB_HOST,
    port: int = DEFAULT_WEB_PORT,
) -> None:
    run_web_runtime(root=root, host=host, port=port)


def build_flask_app(site: SiteDefinition):  # pragma: no cover - runtime only
    app = Flask(__name__)
    navigation = site.navigation_html()

    for route, page in site.pages.items():
        endpoint = "index" if route == "/" else route.strip("/").replace("/", "_")

        def make_view(page: PageDefinition):
            def view():
                return render_template_string(page.render_html(navigation))

            return view

        app.add_url_rule(route, endpoint, make_view(page))

    return app


def run_builtin_server(site: SiteDefinition, *, host: str, port: int) -> None:  # pragma: no cover - runtime only
    navigation = site.navigation_html()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            request_path = self.path.split("?", 1)[0]
            if request_path.endswith("/") and request_path != "/":
                request_path = request_path.rstrip("/")

            page = site.pages.get(request_path)
            if page is None:
                self.send_response(404)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(b"<h1>404</h1><p>MRL page not found.</p>")
                return

            payload = page.render_html(navigation).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, format: str, *args) -> None:
            return

    server = ThreadingHTTPServer((host, port), Handler)
    try:
        server.serve_forever()
    finally:
        server.server_close()
