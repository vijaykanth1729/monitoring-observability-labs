"""Small sample app for the Monitoring & Observability course.

- Exposes Prometheus metrics at /metrics (hand-written text format, no libraries)
- Writes one log line per request to stdout (Alloy ships these to Loki)
- /error triggers a 500 on purpose so learners can see errors in metrics AND logs

Endpoints:
  /         hello, fast
  /work     simulated work, 50-300 ms
  /error    always returns 500 and logs an ERROR line
  /health   returns ok
  /metrics  Prometheus metrics
"""
import os
import random
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(os.environ.get("PORT", "8000"))
START = time.time()

_lock = threading.Lock()
# (method, path, status) -> count
_requests = {}
# path -> [sum_seconds, count]
_durations = {}


def record(method, path, status, seconds):
    with _lock:
        key = (method, path, str(status))
        _requests[key] = _requests.get(key, 0) + 1
        d = _durations.setdefault(path, [0.0, 0])
        d[0] += seconds
        d[1] += 1


def log(level, msg, **fields):
    extra = " ".join(f'{k}={v}' for k, v in fields.items())
    ts = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())
    print(f'ts={ts} level={level} msg="{msg}" {extra}'.rstrip(), flush=True)


def render_metrics():
    lines = []
    lines.append("# HELP app_http_requests_total Total HTTP requests handled.")
    lines.append("# TYPE app_http_requests_total counter")
    with _lock:
        for (method, path, status), n in sorted(_requests.items()):
            lines.append(
                f'app_http_requests_total{{method="{method}",path="{path}",status="{status}"}} {n}'
            )
        lines.append("# HELP app_request_duration_seconds Time spent handling requests.")
        lines.append("# TYPE app_request_duration_seconds summary")
        for path, (total, count) in sorted(_durations.items()):
            lines.append(f'app_request_duration_seconds_sum{{path="{path}"}} {total:.6f}')
            lines.append(f'app_request_duration_seconds_count{{path="{path}"}} {count}')
    lines.append("# HELP app_start_time_seconds Unix time when the app started.")
    lines.append("# TYPE app_start_time_seconds gauge")
    lines.append(f"app_start_time_seconds {START:.0f}")
    return "\n".join(lines) + "\n"


class Handler(BaseHTTPRequestHandler):
    server_version = "sample-app"

    def log_message(self, *args):  # silence default access log; we log ourselves
        pass

    def _send(self, status, body, ctype="text/plain; charset=utf-8"):
        data = body.encode()
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = self.path.split("?")[0]
        began = time.time()

        if path == "/metrics":
            self._send(200, render_metrics(), "text/plain; version=0.0.4; charset=utf-8")
            return

        if path == "/":
            status, body = 200, "hello from the sample app\n"
        elif path == "/health":
            status, body = 200, "ok\n"
        elif path == "/work":
            time.sleep(random.uniform(0.05, 0.3))
            status, body = 200, "work done\n"
        elif path == "/error":
            status, body = 500, "something broke on purpose\n"
        else:
            status, body = 404, "not found\n"
            path = "/other"  # keep label values bounded

        self._send(status, body)
        elapsed = time.time() - began
        record("GET", path, status, elapsed)

        level = "error" if status >= 500 else "info"
        message = "database connection refused" if path == "/error" else "request handled"
        log(level, message,
            method="GET", path=path, status=status, duration_ms=int(elapsed * 1000))


if __name__ == "__main__":
    log("info", "sample app starting", port=PORT)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
