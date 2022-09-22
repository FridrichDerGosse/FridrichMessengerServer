from threading import Thread
import typing as tp
import websockets
import asyncio
import base64
import socket
import json
import time


# com defaults
START_B = bytes(0)
END_B = bytes(1)


class WebSocketServer:
    running: bool = True

    def __init__(self, port: int, client_handler_func: tp.Callable, autostart_client_acceptor: bool = True):
        self._port = port
        self._client_handler_func = client_handler_func

        if autostart_client_acceptor:
            asyncio.run(self.accept_clients())

    @property
    def port(self) -> int:
        return self._port

    async def accept_clients(self):
        while self.running:
            async with websockets.serve(self._client_handler_func, "localhost", self.port):
                await asyncio.Future()


class NSocketServer(socket.socket):
    running: bool = True

    def __init__(self, port: int, client_handler_func: tp.Callable, autostart_client_acceptor: bool = True):
        """
        :param port: the port to run on
        :param client_handler_func: gets called when a new client connects. params: (client: socket.socket, address)
        :param autostart_client_acceptor:
        """
        self._client_func = client_handler_func
        self._port = port

        # initialize parent class
        super().__init__(socket.AF_INET, socket.SOCK_STREAM)
        self.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.bind(("0.0.0.0", self.port))
        self.listen()

        # start accepting thread
        if autostart_client_acceptor:
            Thread(target=self._accept_clients).start()

    @property
    def port(self) -> int:
        """
        the port the server is running on
        """
        return self._port

    def n_send(self, data: dict):
        """
        sends data
        :return: if the message has successfully arrived
        """
        return n_send(data, self)

    def n_recv(self) -> dict | None:
        """
        receives data
        """
        return n_recv(self)

    def _accept_clients(self):

        self.settimeout(.2)
        while self.running:
            try:
                cl, addr = self.accept()

            except (TimeoutError, OSError):
                continue

            Thread(target=self._client_func, args=[NSockExisting(cl), addr]).start()

    def __del__(self):
        self.end()

    def end(self):
        self.close()
        self.running = False


class NSocketClient(socket.socket):
    def __init__(self, host: str, port: int) -> None:
        self._host = host
        self._port = port

        # initialize parent class
        super().__init__(socket.AF_INET, socket.SOCK_STREAM)
        self.connect((self.host, self.port))

    @property
    def host(self) -> str:
        """
        the server host
        """
        return self._host

    @property
    def port(self) -> int:
        """
        the server port
        """
        return self._port

    def n_send(self, data: dict):
        return n_send(data, self)

    def n_recv(self) -> dict | None:
        return n_recv(self)


class NSockExisting:
    """
    creat a NSocket from an already existing socket
    """
    def __init__(self, sock: socket.socket) -> None:
        self._socket = sock

    @property
    def socket(self) -> socket.socket:
        return self._socket

    def n_send(self, data: dict):
        return n_send(data, self._socket)

    def n_recv(self) -> dict | None:
        return n_recv(self._socket)


def n_send(data: dict, sock: socket.socket):
    """
    send a message properly
    """
    msg = {
        "time": time.time(),
        "content": data,
    }

    # send message
    b_mes = json.dumps(msg).encode("ASCII")
    sock.sendall(START_B)
    sock.sendall(base64.b64encode(b_mes))
    sock.sendall(END_B)


def n_recv(sock: socket.socket) -> dict | None:
    """
    receive a message properly
    """
    global START_B, END_B

    msg = b""
    while True:
        new = sock.recv(1)

        if new == START_B:
            # start byte has been received after already receiving data
            if not len(msg) == 0:
                return None

            msg = b""

        elif new == END_B:
            break

        else:
            msg += new

    data = json.loads(base64.b64decode(msg).decode("ASCII"))
    return data["content"]


async def ws_send(data: dict, ws):
    msg = {
        "time": time.time(),
        "content": data,
    }

    try:
        mes = json.dumps(msg)
    except Exception:
        print(f"json encoding error for message: {msg}")
        raise

    await ws.send(mes)


if __name__ == "__main__":
    t = input("Server or client? [s/c] ").lower()
    if t == "s":
        from random import randint

        def recv_func(cl, addr):
            print(type(addr), addr)
            d = cl.n_recv()
            print(f"received: {d}")
            cl.n_send(d)
            serv.end()

        serv = NSocketServer(randint(5_000, 10_000), recv_func)
        print(f"port: {serv.port}")

    elif t == "c":
        cl = NSocketClient(input("host: ").strip(), int(input("port: ")))
        cl.n_send({
            "hellow": "How are you?",
            "b": 5.1,
        })
        d = cl.n_recv()
        print(f"received: {d}")
