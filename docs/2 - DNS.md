## DNS

### The script

There are a lot of details that needs to be handled by the DNS script

```
#!/usr/bin/env python3
"""
Hand-built DNS client: constructs an A-record query with struct, sends it over
UDP to a resolver, then parses the reply (header, question, answer records).

Usage: python3 dns_query.py [domain]      (default: example.com)
"""
import random
import socket
import struct
import sys

RESOLVER_IP = "8.8.8.8"
RESOLVER_PORT = 53
TIMEOUT = 3.0          # seconds to wait for a reply
BUFSIZE = 512          # classic max size of a DNS message over UDP

QTYPE_A = 1            # A record (IPv4 address)
QCLASS_IN = 1          # Internet class
FLAG_RD = 0x0100       # "recursion desired" bit

TYPE_NAMES = {1: "A", 2: "NS", 5: "CNAME", 15: "MX", 16: "TXT", 28: "AAAA"}
RCODES = {0: "NOERROR", 1: "FORMERR", 2: "SERVFAIL", 3: "NXDOMAIN",
          4: "NOTIMP", 5: "REFUSED"}


# ---------------------------------------------------------------- building
def build_header(txid):
    """12-byte header: ID, flags, QDCOUNT, ANCOUNT, NSCOUNT, ARCOUNT."""
    return struct.pack("!HHHHHH", txid, FLAG_RD, 1, 0, 0, 0)


def encode_name(domain):
    """'www.example.com' -> b'\\x03www\\x07example\\x03com\\x00'."""
    encoded = b""
    for label in domain.rstrip(".").split("."):
        raw = label.encode("ascii")
        if not 0 < len(raw) <= 63:
            raise ValueError(f"Invalid label length in {domain!r}")
        encoded += struct.pack("!B", len(raw)) + raw
    return encoded + b"\x00"          # zero byte terminates the name


def build_query(domain, txid):
    question = encode_name(domain) + struct.pack("!HH", QTYPE_A, QCLASS_IN)
    return build_header(txid) + question


# ----------------------------------------------------------------- parsing
def parse_header(data):
    if len(data) < 12:
        raise ValueError("Response shorter than a DNS header")
    txid, flags, qd, an, ns, ar = struct.unpack("!HHHHHH", data[:12])
    return {
        "id": txid,
        "is_response": bool(flags >> 15),
        "rcode": flags & 0x000F,
        "flags": flags,
        "qdcount": qd,
        "ancount": an,
        "nscount": ns,
        "arcount": ar,
    }


def decode_name(data, offset):
    """
    Read a possibly compressed name starting at offset.
    Returns (name, offset_after_name_in_original_position).
    A length byte with the top two bits set (0xC0) is a pointer to
    another place in the message where the rest of the name continues.
    """
    labels = []
    end = None
    hops = 0
    while True:
        length = data[offset]
        if length & 0xC0 == 0xC0:                      # compression pointer
            pointer = ((length & 0x3F) << 8) | data[offset + 1]
            if end is None:
                end = offset + 2
            offset = pointer
            hops += 1
            if hops > 20:
                raise ValueError("Compression pointer loop")
        elif length == 0:                              # end of name
            offset += 1
            break
        else:
            offset += 1
            labels.append(data[offset:offset + length].decode("ascii", "replace"))
            offset += length
    return ".".join(labels), (end if end is not None else offset)


def parse_answers(data, offset, count):
    records = []
    for _ in range(count):
        name, offset = decode_name(data, offset)
        rtype, rclass, ttl, rdlength = struct.unpack("!HHIH", data[offset:offset + 10])
        offset += 10
        rdata = data[offset:offset + rdlength]

        if rtype == 1 and rdlength == 4:
            value = socket.inet_ntoa(rdata)                     # A
        elif rtype == 28 and rdlength == 16:
            value = socket.inet_ntop(socket.AF_INET6, rdata)    # AAAA
        elif rtype == 5:
            value, _ = decode_name(data, offset)                # CNAME
        else:
            value = rdata.hex()

        records.append((name, TYPE_NAMES.get(rtype, str(rtype)), ttl, value))
        offset += rdlength
    return records, offset


# -------------------------------------------------------------------- main
def main():
    domain = sys.argv[1] if len(sys.argv) > 1 else "example.com"
    txid = random.randint(0, 0xFFFF)
    query = build_query(domain, txid)

    print(f"Querying {RESOLVER_IP}:{RESOLVER_PORT} for A record of {domain}")
    print(f"Sent {len(query)} bytes, transaction ID = 0x{txid:04x}")
    print(f"Query hex: {query.hex()}")

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(TIMEOUT)
        sock.sendto(query, (RESOLVER_IP, RESOLVER_PORT))
        try:
            data, addr = sock.recvfrom(BUFSIZE)
        except socket.timeout:
            print(f"No reply within {TIMEOUT} seconds.")
            return

    print(f"\nReceived {len(data)} bytes from {addr[0]}:{addr[1]}")
    header = parse_header(data)

    if header["id"] != txid:
        print(f"Transaction ID mismatch: sent 0x{txid:04x}, "
              f"got 0x{header['id']:04x}. Discarding reply.")
        return
    print(f"Transaction ID matches: 0x{header['id']:04x}")

    print(f"Is response: {header['is_response']}, "
          f"RCODE: {RCODES.get(header['rcode'], header['rcode'])}")
    print(f"Questions: {header['qdcount']}  Answers: {header['ancount']}  "
          f"Authority: {header['nscount']}  Additional: {header['arcount']}")

    # Skip the echoed question section(s): name + 2 bytes type + 2 bytes class
    offset = 12
    for _ in range(header["qdcount"]):
        _, offset = decode_name(data, offset)
        offset += 4

    records, _ = parse_answers(data, offset, header["ancount"])
    for name, rtype, ttl, value in records:
        print(f"  {name}  TTL={ttl}  {rtype}  {value}")


if __name__ == "__main__":
    main()
```
The script is a bit complicated, because everything works in bytes and bits. 

![dns script creation](/screenshots/dns1.png)

Here we create and run the script created above. 

### Domain name

We can change the localhost domain name with "sudo nano /etc/hosts". Then we add the new name to the line with the 127.0.0.1 ip. We keep the original "localhost" so that "localhost" still points to our own machine. 

![domain name change](/screenshots/dns2.png)

After changing the domain name, we ping it to make sure it works. 

![ping network.test](/screenshots/dns3.png)

### Recordtypes

We use nslookup to check different record types

![recordtype A](/screenshots/dns4.png)

Type A: This record maps which IPv4 address to actually connect to. in this case 108.177.96.100 is one of such answers. 

![recordtype CNAME](/screenshots/dns5.png)

Type CNAME: CNAME points to another domain name instead of an IP. in this case we see that "www.github.com" is a CNAME to "github.com". 

![recordtype MX](/screenshots/dns6.png)

Type MX: MX tells other mail servers where to deliver email for that domain. Each MX record has a priority number with lower numbers preferred. A mail server try them in the priority order. In this case the numbers would be 5, 10, 20, 30, 40. 

![recordtype TXT](/screenshots/dns7.png)

Type TXT: TXT is a free-form string attached to a domain. It is mostly used for machine-readable verification and anti-spam policy. We can see 2 verification keys in the screenshot above. 

![recordtype NS](/screenshots/dns8.png)

Type NS: NS tells which nameservers are responsible for answering queries about the domain at all. In our example we can see 4 nameservers of google. ns1.google.com etc. 

### DNS request

We open wireshark to look at a dns-request in realtime

![dns request](/screenshots/dns9.png)

Here we have located the query response, transaction ID and type. 

![TTL](/screenshots/dns10.png)

We can also see the TTL in the answers section. 