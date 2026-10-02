## Integration

### Wireshark

We start wireshark, the https server and use a third terminal to access the server with curl -v https://network.test:8443/ -k. 

![wireshark capture](/screenshots/int1.png)

The first captured segment is a dns call from before we start the call to the server. Other DNS calls are not visible in wireshark, as the host files are checked before DNS is consulted. 

![wireshark capture](/screenshots/int2.png)

In the next section we see the three-way handshake of the TCP protocol. The client sends a packet with [SYN]. The server listens and replies with its own [SYN], and acknowledging the client's [SYN]. Lastly, the client acknowledges the server's [SYN]. 

![wireshark capture](/screenshots/int3.png)

In the overall view, we can see a few more things. 

The next session is TLS where the encryption is. We can see the certification as well. 

Finally the HTTP replies with Application Data. 

### Diagram

Below is a diagram over the wireshark capture process. 

![wireshark capture](/screenshots/int4.png)

### Curl

We can also thee the communication directly in the curl-output of the terminal. 

![wireshark capture](/screenshots/int5.png)

First, the host is resolved and we connect to the server IP on port 8443. Then we see the TLS processing the handshake protocols and verifying the certificate. 

Then we see the SSL connection and the server certificate. We skip the validation of the self-signed certificate as expected and get a public key we use to sign it. 

After this we get the HTTP responses and have successfully accesses the server. 