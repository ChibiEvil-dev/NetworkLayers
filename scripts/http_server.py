#!/usr/bin/env python3
"""
Minimal HTTP server built directly on a TCP socket -- no http.server, no
frameworks. Parses a raw GET request (method, path, headers) and writes
back a hand-formatted HTTP response.

Usage: python3 http_server.py
Then:  curl -v http://127.0.0.1:8080/
       curl -v http://127.0.0.1:8080/missing
"""
import socket

HOST = "127.0.0.1"
PORT = 8080

# Very small "routing table": path -> (content-type, body)
ROUTES = {
    "/": ("text/html", "<html><body><h1>It works</h1></body></html>"),
    "/hello": ("text/plain", "Hello, world!\n"),
}

REASON_PHRASES = {
    200: "OK",
    404: "Not Found",
}


def parse_request(raw_request):
    """
    Parse a raw HTTP request into (method, path, version, headers).
    Returns None if the request line is malformed.
    """
    lines = raw_request.split("\r\n")
    request_line = lines[0]
    parts = request_line.split(" ")
    if len(parts) != 3:
        return None
    method, path, version = parts

    headers = {}
    for line in lines[1:]:
        if not line:            # blank line marks end of headers
            break
        if ":" not in line:
            continue
        name, _, value = line.partition(":")
        headers[name.strip().lower()] = value.strip()

    return method, path, version, headers


def build_response(status_code, content_type, body):
    """Build a full HTTP/1.1 response as bytes, status line + headers + body."""
    reason = REASON_PHRASES.get(status_code, "Unknown")
    body_bytes = body.encode("utf-8")

    status_line = f"HTTP/1.1 {status_code} {reason}\r\n"
    headers = (
        f"Content-Type: {content_type}\r\n"
        f"Content-Length: {len(body_bytes)}\r\n"
        f"Connection: close\r\n"
    )
    return (status_line + headers + "\r\n").encode("utf-8") + body_bytes


def handle_request(raw_request):
    """Turn a raw request string into a response bytes object."""
    parsed = parse_request(raw_request)
    if parsed is None:
        return build_response(400, "text/plain", "Bad Request\n")

    method, path, version, headers = parsed
    print(f"  {method} {path} {version}")
    for name, value in headers.items():
        print(f"    {name}: {value}")

    if method != "GET":
        return build_response(404, "text/plain", "Not Found\n")

    if path in ROUTES:
        content_type, body = ROUTES[path]
        return build_response(200, content_type, body)

    return build_response(404, "text/html", "<html><body><h1>404 Not Found</h1></body></html>")


def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((HOST, PORT))
        server.listen()
        print(f"HTTP server listening on http://{HOST}:{PORT} (Ctrl+C to stop)")

        try:
            while True:
                conn, addr = server.accept()
                with conn:
                    print(f"\nConnection from {addr}")
                    # A GET request has no body, so one recv() is normally
                    # enough to get the whole thing (request line + headers).
                    data = conn.recv(4096)
                    if not data:
                        continue
                    raw_request = data.decode("utf-8", errors="replace")

                    response = handle_request(raw_request)
                    conn.sendall(response)
        except KeyboardInterrupt:
            print("\nServer stopped.")


if __name__ == "__main__":
    main()
