import json
import queue
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).parent
PORT = 8765
FILES = {
    "/": ("avatar.html", "text/html; charset=utf-8"),
    "/model.vrm": ("model.vrm", "application/octet-stream"),
}

listeners = []
lock = threading.Lock()


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/events":
            return self.stream()
        if self.path not in FILES:
            return self.send_error(404)
        name, kind = FILES[self.path]
        data = (HERE / name).read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        if self.path != "/event":
            return self.send_error(404)
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        self.send_response(204)
        self.end_headers()
        try:
            event = json.loads(body)
        except ValueError:
            return
        message = json.dumps({"event": event.get("hook_event_name"), "tool": event.get("tool_name")})
        with lock:
            for q in listeners:
                q.put(message)

    def stream(self):
        q = queue.Queue()
        with lock:
            listeners.append(q)
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        try:
            while True:
                try:
                    self.wfile.write(f"data: {q.get(timeout=15)}\n\n".encode())
                except queue.Empty:
                    self.wfile.write(b": ping\n\n")
                self.wfile.flush()
        except OSError:
            pass
        finally:
            with lock:
                listeners.remove(q)

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    print(f"Avatar running at http://127.0.0.1:{PORT}")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
