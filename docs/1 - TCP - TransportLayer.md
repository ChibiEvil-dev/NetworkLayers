## TCP - TransportLayer

### Wireshark

We use the Linux Server from our first assignment and boot it up without gui. We connect to the server with ssh via powershell from our local machine. 

```
ssh -p 2222 secureadmin@127.0.0.1
```
We need to make sure that we are working directly on the server for this, and we do this by checking the details with "hostname" and "ip a". we see that we are indeed located on the server for this session. 

We install wireshark and realize that we need GUI on the server in order to run and use wireshark. For that reason we need to install a gui on the server. 

```
sudo apt install xfce4 xrdp wireshark
sudo adduser xrdp ssl-cert
echo xfce4-session > ~/.xsession
sudo systemctl enable --now xrdp
```
In theory this should work, but I ran into some issues. I could not log in to the server with GUI. 
I found out, that in my current setup, it tries to boot into an "ubunto" session, which does not exist. 

![setup1](/screenshots/tcp1.png)

The above lines enabled me to log into the right session and opening the system with the GUI. 

Now we can use the applications menu to open wireshark on the server by using "sudo wireshark". 
Sudo isn't optimal for this, so we use "sudo usermod -aG wireshark adminidude" to add permissions to run it without sudo. This is confirmed to work after a reboot. 

### TCP server

To create the simple TCP echo-server, we use "nano echo_server.py" and "nano echo_client.py" to create the 2 python scripts. 

```
#echo_server.py
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
```
```
#echo_client.py
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
```
We open both in 2 seperate terminals. 

![echo server communication](/screenshots/tcp2.png)

We can see that the text message is received on the server and visible in wireshark. 

![echo client communication](/screenshots/tcp3.png)

We can follow the communication packages in wireshark. relevant info has been underlined. 

### TCP vs UDP

TCP works reliably. it ensures delivery of the full data, and tries to retransmit if a package is lost. Data also arrives in the exact order it was sent. 

UDP sends the raw data and lets the application work for it. It doesn't care about the order of packets and any lost package stay lost. 

HTTP transfers documents, and is therefore only usefull with TCP, as the data arrives in the correct order and not scrambled. 

Real-time media has the opposite need, a late packet is useless after the moment has passed, so it skips and waits for the next packet instead. 

![active connection](/screenshots/tcp4.png)

Here we see the active connection from the client to the server. 