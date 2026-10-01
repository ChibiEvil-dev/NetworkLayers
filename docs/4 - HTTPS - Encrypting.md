## HTTPS/TLS

### Certificate

Now we will create a key and certificate for securing HTTP-trafic. 

```
openssl req -x509 -newkey rsa:2048 -keyout network.test.key -out network.test.crt \
  -days 365 -nodes -subj "/CN=network.test" \
  -addext "subjectAltName=DNS:network.test"
```
We use req -x509 to skip waiting for a real CA to sign, as we are acting as our own CA in this case. 
The private key is valid in 365 days and is written to the network.test domain. 

-addext is used to make sure that the certificate is treated as valid across many clients. 

![certificate generation](/screenshots/tls1.png)

We can see the generation when we run the command. 

![certificate generation](/screenshots/tls2.png)

![certificate generation](/screenshots/tls3.png)

Here we verify the key we just generated. 

### HTTPS

We create a new python script for the HTTPS server, using a different port to avoid collisions. 

```
#!/usr/bin/env python3
"""
Same raw HTTP server as before, now speaking TLS. The request parsing and
response building are completely unchanged -- only the socket is different.

Needs a certificate and key next to this script (see: openssl req -x509 ...
from earlier). Defaults match the network.test cert we generated.

Usage: python3 https_server.py
Then:  curl -k https://network.test:8443/          (needs /etc/hosts entry)
       curl -k --resolve network.test:8443:127.0.0.1 https://network.test:8443/

Optional: set SSLKEYLOGFILE to have Wireshark decrypt the traffic, e.g.
       SSLKEYLOGFILE=$PWD/keylog.txt python3 https_server.py
"""
import os
import socket
import ssl

HOST = "127.0.0.1"
PORT = 8443
CERT_FILE = "network.test.crt"
KEY_FILE = "network.test.key"

ROUTES = {
    "/": ("text/html", "<html><body><h1>It works (over TLS)</h1></body></html>"),
    "/hello": ("text/plain", "Hello, world!\n"),
}

REASON_PHRASES = {
    200: "OK",
    404: "Not Found",
}


def parse_request(raw_request):
    lines = raw_request.split("\r\n")
    request_line = lines[0]
    parts = request_line.split(" ")
    if len(parts) != 3:
        return None
    method, path, version = parts

    headers = {}
    for line in lines[1:]:
        if not line:
            break
        if ":" not in line:
            continue
        name, _, value = line.partition(":")
        headers[name.strip().lower()] = value.strip()

    return method, path, version, headers


def build_response(status_code, content_type, body):
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


def build_ssl_context():
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certfile=CERT_FILE, keyfile=KEY_FILE)

    # If SSLKEYLOGFILE is set, log session keys there so Wireshark can
    # decrypt the capture. Off by default -- only happens if you ask for it.
    keylog_path = os.environ.get("SSLKEYLOGFILE")
    if keylog_path:
        context.keylog_filename = keylog_path
        print(f"Logging TLS session keys to {keylog_path}")

    return context


def main():
    context = build_ssl_context()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((HOST, PORT))
        server.listen()
        print(f"HTTPS server listening on https://{HOST}:{PORT} (Ctrl+C to stop)")

        try:
            while True:
                conn, addr = server.accept()
                try:
                    # Wrap the plain TCP connection in TLS. This performs
                    # the handshake (ClientHello/ServerHello/certificate
                    # exchange) before returning.
                    with context.wrap_socket(conn, server_side=True) as secure_conn:
                        print(f"\nConnection from {addr}")
                        print(f"  TLS version: {secure_conn.version()}, "
                              f"cipher: {secure_conn.cipher()[0]}")

                        data = secure_conn.recv(4096)
                        if not data:
                            continue
                        raw_request = data.decode("utf-8", errors="replace")

                        response = handle_request(raw_request)
                        secure_conn.sendall(response)
                except ssl.SSLError as e:
                    print(f"TLS handshake failed with {addr}: {e}")
                    conn.close()
        except KeyboardInterrupt:
            print("\nServer stopped.")


if __name__ == "__main__":
    main()
```

We can test the server with 
```
curl -k https://network.test:8443/
```
The difference between the http and https server file is minimal, as TLS exists on the socket layer. 

The main difference is the SSLContext which loads the certificate and key onto the server. 

### SSL connection

We test the connection with openssl and connect a client to the https server. 

![HTTPS connection](/screenshots/https1.png)

In the first section we see the connection is established and we see the certificate it uses for verification. 

![HTTPS connection](/screenshots/https2.png)

In the second section we see that the certificate is handled and a new SSL-Session is approved with a key. 

![HTTPS connection](/screenshots/https3.png)

The third section is mostly a repeat of the second section. 

![HTTPS connection](/screenshots/https4.png)

Hereafter the output ends and we are connected to the HTTPS server successfully. 

### Wireshark

We open wireshark, look at the lo port, start the https server and connect the client. Then we look at what wireshark captures. 

![HTTPS connection](/screenshots/https5.png)

As opposed to the http server, we can now see that we connect via TLS and handshake key and certificate is handled. 