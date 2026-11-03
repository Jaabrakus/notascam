#!/usr/bin/env python3
"""Sign-in links for players who play in a browser on the server directly (engine/web/, U4 of
planning/SERVER_UPGRADES_PLAN_2026-10-30.md).

    python3 -I tools/web_token.py --new-secret FILE                  a new secret (64 hex characters, only you can read it)
    python3 -I tools/web_token.py --secret-file FILE --key ACCOUNT   a sign-in link for ACCOUNT, good for 5 minutes, once
        [--minutes M] [--url http://127.0.0.1:12480/?overlay]

The server takes the same file (RM_WEB_SECRET_FILE) and then lets only signed-in players join. A token is
"1.<payload>.<signature>": the payload is base64url JSON {"key": the account, "exp": unix seconds}, the signature
base64url HMAC-SHA256 of "1.<payload>" with the secret. An account service (the Discord link service, later) makes
the same token after a player signs in and sends them to <server>/join?token=... . The key is the player's DM key:
their saves and units go by it. Never print or share the secret."""
import argparse
import base64
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import secrets
import sys
import time
import urllib.parse


def b64url(data):
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('ascii')


def make_token(secret, key, minutes=5, now=None):
    exp = int((now or time.time()) + minutes * 60)
    payload = b64url(json.dumps({'key': key, 'exp': exp}, separators=(',', ':')).encode('utf-8'))
    signed = '1.' + payload
    return signed + '.' + b64url(hmac.new(secret.encode('utf-8'), signed.encode('ascii'), hashlib.sha256).digest())


def read_secret(path):
    secret = Path(path).read_text().strip()
    if len(secret) < 32: raise SystemExit(f'the secret in {path} is shorter than 32 characters')
    return secret


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--new-secret', metavar='FILE', help='write a new secret to FILE (it must not exist)')
    ap.add_argument('--secret-file', metavar='FILE')
    ap.add_argument('--key', help='the account: 1 to 64 letters, digits, space, _ . @ : -, starting with a letter or digit')
    ap.add_argument('--minutes', type=float, default=5, help='how long the link is good for (at most 60)')
    ap.add_argument('--url', default='http://127.0.0.1:12480/?overlay', help="the server's address, with the page's own options")
    a = ap.parse_args()
    if a.new_secret:
        path = Path(a.new_secret)
        if path.exists(): raise SystemExit(f'{path} exists already; a new secret would sign out every link made with it')
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w') as f: f.write(secrets.token_hex(32) + '\n')
        print(f'wrote a new secret to {path}')
        return 0
    if not a.secret_file or not a.key: ap.error('--secret-file and --key (or --new-secret)')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9 _.@:-]{0,63}', a.key): ap.error('--key: 1 to 64 letters, digits, space, _ . @ : -')
    if not 0 < a.minutes <= 60: ap.error('--minutes: more than 0, at most 60')
    token = make_token(read_secret(a.secret_file), a.key, a.minutes)
    parts = urllib.parse.urlsplit(a.url)
    query = '&'.join(q for q in [parts.query, 'token=' + token] if q)
    print(urllib.parse.urlunsplit((parts.scheme, parts.netloc, '/join', query, '')))
    return 0


if __name__ == '__main__':
    sys.exit(main())
