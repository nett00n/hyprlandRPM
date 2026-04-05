import http.server
import socketserver
import ssl
import logging
import argparse
import subprocess
from pathlib import Path
from functools import partial

DEFAULT_PORT = 8000
CERT_FILE = "server.pem"


def ensure_cert(cert_file: Path):
    if cert_file.exists():
        return

    logging.info("Generating self-signed certificate...")
    subprocess.run(
        [
            "openssl",
            "req",
            "-new",
            "-x509",
            "-keyout",
            str(cert_file),
            "-out",
            str(cert_file),
            "-days",
            "365",
            "-nodes",
            "-subj",
            "/CN=localhost",
        ],
        check=True,
    )
    logging.info(f"Certificate generated at {cert_file}")


def wrap_ssl(httpd, cert_file: Path):
    ensure_cert(cert_file)
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(certfile=str(cert_file))
    httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)


class GetHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        logging.info("%s - Headers:\n%s", self.client_address, self.headers)
        super().do_GET()

    def list_directory(self, path):
        """Override to inject simple CSS for autoindex pages."""
        from html import escape
        from io import BytesIO
        import os

        try:
            entries = os.listdir(path)
        except OSError:
            self.send_error(404, "No permission to list directory")
            return None

        entries.sort(key=lambda a: a.lower())
        displaypath = escape(self.path)

        css = """
        body { font-family: sans-serif; margin: 2rem; background: #fafafa; }
        h1 { font-size: 1.4rem; }
        ul { list-style: none; padding: 0; }
        li { margin: 0.2rem 0; }
        a { text-decoration: none; color: #0366d6; }
        a:hover { text-decoration: underline; }
        .dir { font-weight: bold; }
        """

        r = []
        r.append("<!DOCTYPE html><html><head><meta charset='utf-8'>")
        r.append(f"<title>Index of {displaypath}</title>")
        r.append(f"<style>{css}</style></head><body>")
        r.append(f"<h1>Index of {displaypath}</h1><ul>")

        for name in entries:
            fullname = os.path.join(path, name)
            display = link = name
            if os.path.isdir(fullname):
                display = name + "/"
                link = name + "/"
                cls = "dir"
            else:
                cls = ""
            r.append(f"<li><a class='{cls}' href='{link}'>{display}</a></li>")

        r.append("</ul></body></html>")

        encoded = "\n".join(r).encode("utf-8", "surrogateescape")

        f = BytesIO()
        f.write(encoded)
        f.seek(0)

        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        return f


def parse_args():
    p = argparse.ArgumentParser(description="Simple HTTP/HTTPS file server")
    p.add_argument("-s", "--ssl", action="store_true", help="Enable HTTPS")
    p.add_argument("-b", "--base-dir", default=".", help="Directory to serve")
    p.add_argument("-p", "--port", type=int, default=DEFAULT_PORT)
    p.add_argument("--host", default="0.0.0.0", help="Host to bind (default: 0.0.0.0)")
    return p.parse_args()


def main():
    logging.basicConfig(level=logging.INFO)
    args = parse_args()

    base_dir = Path(args.base_dir).resolve()
    if not base_dir.exists():
        logging.error("Base directory does not exist: %s", base_dir)
        return

    handler = partial(GetHandler, directory=str(base_dir))
    httpd = socketserver.ThreadingTCPServer((args.host, args.port), handler)

    if args.ssl:
        wrap_ssl(httpd, Path(CERT_FILE))

    proto = "HTTPS" if args.ssl else "HTTP"
    logging.info("Serving %s on %s:%s, dir=%s", proto, args.host, args.port, base_dir)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logging.info("Shutting down...")
        httpd.server_close()


if __name__ == "__main__":
    main()
