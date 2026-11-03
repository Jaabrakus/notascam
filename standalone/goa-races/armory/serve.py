"""Serve the self-contained armory locally without modifying the game or converter."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import argparse
import threading
import webbrowser

HERE = Path(__file__).resolve().parent
FILES = {'/': ('index.html', 'text/html; charset=utf-8'),
         '/index.html': ('index.html', 'text/html; charset=utf-8'),
         '/catalog.json': ('catalog.json', 'application/json'),
         '/gear.csv': ('Universal Gear and Weapons.csv', 'text/csv; charset=utf-8')}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def do_GET(self):
        path = self.path.split('?', 1)[0]
        if path not in FILES:
            self.send_error(404)
            return
        filename, content_type = FILES[path]
        data = (HERE / filename).read_bytes()
        self.send_response(200)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(data)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8877)
    parser.add_argument('--open', action='store_true')
    args = parser.parse_args()
    try:
        server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    except OSError:
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    url = f'http://127.0.0.1:{server.server_address[1]}/'
    print('GOA Universal Armory: ' + url, flush=True)
    if args.open:
        threading.Timer(.4, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
