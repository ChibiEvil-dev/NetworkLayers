#!/usr/bin/env python3
"""Simple TCP echo server: sends back whatever text it receives."""
import socket

HOST = "127.0.0.1"
PORT = 5000


def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        # Allow quick restarts without "Address already in use" errors
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((HOST, PORT))
        server.listen()
        print(f"Echo server listening on {HOST}:{PORT} (Ctrl+C to stop)")

        try:
            while True:
                conn, addr = server.accept()
                with conn:
                    print(f"Connected by {addr}")
                    while True:
                        data = conn.recv(1024)
                        if not data:  # empty bytes = client closed the connection
                            break
                        print(f"Received: {data.decode('utf-8', errors='replace')!r}")
                        conn.sendall(data)
                    print(f"Disconnected {addr}")
        except KeyboardInterrupt:
            print("\nServer stopped.")


if __name__ == "__main__":
    main()
