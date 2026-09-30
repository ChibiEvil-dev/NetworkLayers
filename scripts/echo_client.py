#!/usr/bin/env python3
"""Simple TCP echo client: sends typed text to the server and prints the echo."""
import socket

HOST = "127.0.0.1"
PORT = 5000


def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
        try:
            client.connect((HOST, PORT))
        except ConnectionRefusedError:
            print(f"Could not connect to {HOST}:{PORT}. Is the server running?")
            return

        print(f"Connected to {HOST}:{PORT}. Type a message, or 'quit' to exit.")
        while True:
            try:
                message = input("> ")
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if message.strip().lower() == "quit":
                break
            if not message:
                continue

            client.sendall(message.encode("utf-8"))
            reply = client.recv(1024)
            if not reply:
                print("Server closed the connection.")
                break
            print(f"Echo: {reply.decode('utf-8', errors='replace')}")


if __name__ == "__main__":
    main()
