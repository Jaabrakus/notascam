"""Serve only the Orc review folder on this computer and open its viewer."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import webbrowser

parser=argparse.ArgumentParser()
parser.add_argument('--no-browser',action='store_true')
parser.add_argument('--port',type=int,default=8884)
args=parser.parse_args()
root=Path(__file__).resolve().parent
handler=partial(SimpleHTTPRequestHandler,directory=str(root))
for port in range(args.port,args.port+10):
    try:
        server=ThreadingHTTPServer(('127.0.0.1',port),handler)
        break
    except OSError:
        if port==args.port+9:raise
url=f'http://127.0.0.1:{port}/curated-attacks-v1/'
print(url,flush=True)
if not args.no_browser:webbrowser.open(url)
try:server.serve_forever()
except KeyboardInterrupt:pass
finally:server.server_close()
