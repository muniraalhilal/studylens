"""Start an isolated no-signup demo behind a temporary Cloudflare HTTPS URL.

Requires the official cloudflared executable on PATH, or --cloudflared PATH.
Run from the StudyLens folder: python scripts/share_demo.py
Ctrl+C stops both processes. Never points the tunnel at the personal database.
"""

import argparse
import json
import os
from pathlib import Path
import queue
import re
import signal
import subprocess
import sys
import threading
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cloudflared", default="cloudflared")
    parser.add_argument("--port", type=int, default=8001)
    args = parser.parse_args()
    # Fail without exposing anything when another service already owns the port.
    import socket

    with socket.socket() as check:
        check.bind(("127.0.0.1", args.port))
    (ROOT / "data").mkdir(exist_ok=True)
    tunnel = None
    server = None
    try:
        tunnel = subprocess.Popen(
            [
                args.cloudflared,
                "tunnel",
                "--no-autoupdate",
                "--protocol",
                "http2",
                "--url",
                f"http://127.0.0.1:{args.port}",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        lines = queue.Queue()

        def read_logs():
            for line in tunnel.stdout:
                lines.put(line)

        threading.Thread(target=read_logs, daemon=True).start()
        deadline = time.monotonic() + 90
        url = None
        while time.monotonic() < deadline:
            if tunnel.poll() is not None:
                raise RuntimeError("The tunnel could not start. Check your network connection.")
            try:
                line = lines.get(timeout=1)
            except queue.Empty:
                continue
            match = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", line)
            if match:
                url = match.group(0)
                break
        if not url:
            raise RuntimeError("No public URL was received within 90 seconds.")
        print(f"Checking temporary URL: {url}", flush=True)
        environment = dict(os.environ)
        environment.update(
            {
                "DATABASE_URL": f"sqlite:///{ROOT / 'data/public-demo.db'}",
                "APP_ORIGIN": url,
                "PUBLIC_DEMO_ONLY": "true",
                "COOKIE_SECURE": "true",
                "TRUST_CLOUDFLARE": "true",
            }
        )
        server = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "backend.app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(args.port),
                "--no-proxy-headers",
            ],
            cwd=ROOT,
            env=environment,
        )

        # Drain tunnel output continuously to avoid pipe backpressure.
        def drain():
            while tunnel.poll() is None:
                try:
                    line = lines.get(timeout=1)
                    if " ERR " in line:
                        print(line.strip(), flush=True)
                except queue.Empty:
                    pass

        threading.Thread(target=drain, daemon=True).start()
        verified = False
        for _ in range(30):
            if server.poll() is not None:
                raise RuntimeError("StudyLens server failed to start.")
            try:
                with urllib.request.urlopen(url + "/api/health", timeout=5) as response:
                    verified = json.load(response).get("database") == "ok"
            except Exception as exc:
                if _ in {0, 10, 20}:
                    print(f"Waiting for public health check: {exc}", flush=True)
                time.sleep(1)
            if verified:
                break
        if not verified:
            raise RuntimeError("The public URL could not be verified; no share link was published.")
        (ROOT / "data/share-session.json").write_text(json.dumps({"url": url, "temporary": True}))
        print(
            f"\nSHARE_URL={url}\nTemporary link: keep this process and your computer running. Ctrl+C to stop.\n",
            flush=True,
        )
        while server.poll() is None and tunnel.poll() is None:
            time.sleep(1)
    finally:
        for process in (server, tunnel):
            if process and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
        (ROOT / "data/share-session.json").unlink(missing_ok=True)


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    try:
        main()
    except KeyboardInterrupt:
        print("\nSharing stopped.")
