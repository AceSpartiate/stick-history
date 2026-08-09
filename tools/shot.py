# -*- coding: utf-8 -*-
"""A one-file capture endpoint, so a canvas in the page can be LOOKED AT.

WHY THIS EXISTS: the browser pane stops compositing after a few calls, and the only other
way to get a rendered canvas out of the page was to pull its base64 through the tool return
and write it back to disk - which costs the image twice in context, per look. Six commits in
this project have said "verified as structure, not as a picture" and every drawing fault we
have had came from not looking. Looking has to be cheap or it does not happen.

The page POSTs a data URL here; this writes the PNG next to it. That is all it does. It is a
DEVELOPMENT TOOL - it is not part of the game, it is never served to a player, and index.html
has no idea it exists (the zero-network, single-file promise is untouched).

    python tools/shot.py            # serves on 8124, writes into tools/shots/

Then, in the page:

    fetch('http://localhost:8124/shot?name=james',
          {method:'POST', body: canvas.toDataURL('image/png')})
"""
import base64
import os
import sys

try:
    from http.server import BaseHTTPRequestHandler, HTTPServer
except ImportError:                                   # python 2
    from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "shots")
PORT = 8124


class Shot(BaseHTTPRequestHandler):
    def _cors(self):
        # the page is on :8123 and we are on :8124, so this is cross-origin by construction
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_POST(self):
        name = "shot"
        if "?" in self.path:
            for pair in self.path.split("?", 1)[1].split("&"):
                if pair.startswith("name="):
                    name = "".join(c for c in pair[5:] if c.isalnum() or c in "-_")
        n = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(n).decode("ascii", "replace")
        if "," in body:
            body = body.split(",", 1)[1]
        ext = "png"
        path = os.path.join(OUT, name + "." + ext)
        with open(path, "wb") as f:
            f.write(base64.b64decode(body))
        sys.stderr.write("wrote %s (%d bytes)\n" % (path, os.path.getsize(path)))
        sys.stderr.flush()
        self.send_response(200)
        self._cors()
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    if not os.path.isdir(OUT):
        os.makedirs(OUT)
    sys.stderr.write("shot endpoint on http://localhost:%d -> %s\n" % (PORT, OUT))
    sys.stderr.flush()
    HTTPServer(("127.0.0.1", PORT), Shot).serve_forever()
