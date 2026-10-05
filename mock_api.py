"""
Lightweight Mock REST API server for student academic data.
Uses Python's standard library http.server for zero external dependencies.
"""
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
from pathlib import Path
import threading
import time

MOCK_DATA_PATH = Path("data/raw/students_api.json")


class MockAPIHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/api/students"):
            if not MOCK_DATA_PATH.exists():
                self.send_response(404)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Mock data file not found"}).encode("utf-8"))
                return

            with open(MOCK_DATA_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(data).encode("utf-8"))
        elif self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "healthy"}).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        # Suppress standard logging to keep console clean
        pass


def start_background_mock_server(host: str = "127.0.0.1", port: int = 8000) -> HTTPServer:
    """Start the mock server in a background daemon thread."""
    server = HTTPServer((host, port), MockAPIHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.1)  # Allow server to bind
    return server


if __name__ == "__main__":
    port = 8000
    server = HTTPServer(("127.0.0.1", port), MockAPIHandler)
    print(f"Mock REST API running on http://127.0.0.1:{port}/api/students")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping mock server.")
        server.server_close()
