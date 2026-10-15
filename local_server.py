"""Local receipt reader for the normal-Chrome extension. No browser launch."""
import base64
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")
from screenshot_ai import client, extract, dropdown_choice

ITEMS = [
    ("Men's Short Sleeve Striped Johnny Collar Sweater", "", "30.00"),
    ("Men's 7-inch Elevated Linen Shorts", "Goodfellow & Co.", "30.00"),
    ("Men's Short Sleeve Blanket Stitch Button-Down Shirt", "", "30.00"),
    ("Men's 7-inch Whip Stitch Pull-On Shorts", "Goodfellow & Co.", "30.00"),
    ("Women's Strapless Tube Tiered Mini Dress", "Wild Fable", "35.00"),
]

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # No receipts, keys, or request bodies in HTTP logs.

    def allowed(self):
        origin = self.headers.get("Origin", "")
        return origin.startswith("chrome-extension://") and self.headers.get("Host") == "127.0.0.1:18765"

    def respond(self, status, payload):
        data = json.dumps(payload).encode()
        self.send_response(status)
        if self.allowed():
            self.send_header("Access-Control-Allow-Origin", self.headers["Origin"])
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self):
        if not self.allowed():
            self.respond(403, {"error": "Extension requests only."})
            return
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", self.headers["Origin"])
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.end_headers()

    def do_POST(self):
        if not self.allowed():
            self.respond(403, {"error": "Extension requests only."})
            return
        try:
            size = int(self.headers.get("Content-Length", 0))
            if not 0 < size < 115 * 1024 * 1024:
                raise ValueError("Request is too large or empty.")
            body = json.loads(self.rfile.read(size))
            if self.path == "/extract":
                images = body["images"]
                if not 1 <= len(images) <= 20:
                    raise ValueError("Select 1–20 images.")
                with TemporaryDirectory(prefix="amex-receipts-") as directory:
                    paths = []
                    total = 0
                    for i, entry in enumerate(images):
                        name = Path(entry["name"]).name
                        if Path(name).suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
                            raise ValueError("Use PNG, JPG, or WebP images.")
                        data = base64.b64decode(entry["data"], validate=True)
                        total += len(data)
                        if len(data) > 20 * 1024 * 1024 or total > 80 * 1024 * 1024:
                            raise ValueError("Images must be under 20 MB each and 80 MB total.")
                        path = Path(directory) / (f"{i+1:02d}_" + name)
                        path.write_bytes(data)
                        paths.append(path)
                    self.respond(200, {"items": extract(paths)})
            elif self.path == "/choices":
                labels = body["labels"]
                if not isinstance(labels, list) or not 1 <= len(labels) <= 200 or any(not isinstance(s,str) or len(s)>300 for s in labels):
                    raise ValueError("Invalid dropdown choices.")
                self.respond(200, {"index": dropdown_choice(labels, body["target"][:300])})
            else:
                self.respond(404, {"error": "Unknown endpoint."})
        except (ValueError, KeyError) as exc:
            self.respond(400, {"error": str(exc)[:300]})
        except RuntimeError as exc:
            self.respond(500, {"error": str(exc)[:600]})
        except Exception as exc:
            self.respond(500, {"error": f"Receipt/AI operation failed ({type(exc).__name__}). Check Terminal, API billing, model access, and screenshots."})

if __name__ == "__main__":
    client()
    try:
        server = ThreadingHTTPServer(("127.0.0.1", 18765), Handler)
    except OSError:
        raise SystemExit("Port 18765 is already in use. If this helper is running in another Terminal, use that instance; otherwise report the conflict.")
    print("Ready for the Amex Clothing Helper Chrome extension at 127.0.0.1:18765.")
    print("Keep this Terminal running. Use your normal Chrome login; no automated browser is opened.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
