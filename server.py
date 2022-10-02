#!/usr/bin/python3

import io
import socket


class HTTPRequestParser(object):
    def __init__(self):
        self._state = "request_line"
        self._buf = io.BytesIO()
        self._request_line = None
        self.headers = []
        self._content_length = 0
        self.body = b""

    def putc(self, c):
        if self._state == "done":
            raise ValueError("Parser is done")
        getattr(self, f"_putc_{self._state}")(c)
        return self._state == "done"

    def _putc_request_line(self, c):
        if c == b"\n":
            line = self._buf.getvalue()
            if line.endswith(b"\r"):
                self._request_line = line[:-1].decode("utf-8")
                self._buf.truncate(0)
                self._buf.seek(0)
                self._state = "headers"
            else:
                raise ValueError("Invalid request line")
        else:
            self._buf.write(c)

    def _putc_headers(self, c):
        if c == b"\n":
            line = self._buf.getvalue()
            if line.endswith(b"\r"):
                line = line[:-1]
                if line:
                    header = line.decode("utf-8")
                    parts = header.split(":", 1)
                    if len(parts) != 2:
                        raise ValueError("Invalid header")
                    name, value = parts
                    name = name.strip()
                    value = value.strip()
                    self.headers.append((name, value))
                    if name.lower() == "content-length":
                        self._content_length = int(value)
                elif self._content_length:
                    self._state = "body"
                else:
                    self._state = "done"

                self._buf.truncate(0)
                self._buf.seek(0)
        else:
            self._buf.write(c)

    def _putc_body(self, c):
        if not self._content_length:
            raise ValueError("No content length")
        self._buf.write(c)
        body = self._buf.getvalue()
        if len(body) >= self._content_length:
            self._state = "done"
            self.body = body


sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.bind(("", 8080))
sock.listen()

try:
    while True:
        client, addr = sock.accept()
        parser = HTTPRequestParser()
        c = client.recv(1, 0)
        try:
            while not parser.putc(c):
                c = client.recv(1, 0)
            print(parser._request_line)

            buf = io.StringIO()
            for name, value in parser.headers:
                buf.write(f"{name}: {value}\r\n")
            body = buf.getvalue().encode("utf-8")

            client.sendall(b"HTTP/1.1 200 OK\r\n")
            client.sendall(
                b"Content-Length: " + str(len(body)).encode("utf-8") + b"\r\n"
            )
            client.sendall(b"\r\n")
            client.sendall(body)
        except ValueError as e:
            print(e)
            client.sendall(b"HTTP/1.1 400 Bad Request\r\n\r\n")
        client.close()
finally:
    sock.close()
