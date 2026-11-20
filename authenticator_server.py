"""
Serves the phone authenticator (authenticator/) on the local network.

The page only *loads* from here; every OTP is computed on the phone itself
from the secret stored at pairing time, with no network round-trip.
"""

import functools
import os
import socket
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

AUTH_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "authenticator")
AUTH_PORT = int(os.getenv("AUTH_PORT", "8600"))


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


def lan_ip() -> str:
    """Best guess at this laptop's address on the Wi-Fi / hotspot network."""
    override = os.getenv("AUTH_HOST")
    if override:
        return override
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))  # no packet is sent; just picks the outbound interface
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def start_server(port: int = AUTH_PORT) -> bool:
    """Start the static server in a daemon thread. Returns False if the port is taken."""
    handler = functools.partial(_QuietHandler, directory=AUTH_DIR)
    try:
        httpd = ThreadingHTTPServer(("0.0.0.0", port), handler)
    except OSError:
        return False  # already running (e.g. from a previous Streamlit session)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return True


def base_url(host: str | None = None) -> str:
    return f"http://{host or lan_ip()}:{AUTH_PORT}/"


if __name__ == "__main__":
    start_server()
    print(f"Authenticator at {base_url()} (Ctrl+C to stop)")
    threading.Event().wait()
