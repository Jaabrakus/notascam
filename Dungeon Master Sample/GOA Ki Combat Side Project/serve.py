"""Start the standalone experiment from any directory. Standard library only."""
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
import argparse,webbrowser

parser=argparse.ArgumentParser();parser.add_argument('--no-browser',action='store_true');parser.add_argument('--port',type=int,default=8879)
args=parser.parse_args();root=Path(__file__).resolve().parent
handler=partial(SimpleHTTPRequestHandler,directory=str(root))
for port in range(args.port,args.port+10):
    try:server=ThreadingHTTPServer(('127.0.0.1',port),handler);break
    except OSError:
        if port==args.port+9:raise
url=f'http://127.0.0.1:{port}/'
print(f'GOA Ki Combat: {url}',flush=True)
if not args.no_browser:webbrowser.open(url)
try:server.serve_forever()
except KeyboardInterrupt:pass
finally:server.server_close()
