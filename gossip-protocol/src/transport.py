import socket
import threading
import logging
from typing import Callable, Optional

class Transport:
    def send(self, addr: tuple, data: bytes):
        raise NotImplementedError

    def start(self, on_receive: Callable[[bytes, tuple], None]):
        raise NotImplementedError

    def stop(self):
        raise NotImplementedError

class UDPTransport(Transport):
    def __init__(self, host: str, port: int, buffer_size: int = 4096):
        self.host = host
        self.port = port
        self.buffer_size = buffer_size
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.running = False
        self.listen_thread = None
        self._on_receive = None
        self.logger = logging.getLogger(f"UDPTransport-{host}:{port}")

    def start(self, on_receive: Callable[[bytes, tuple], None]):
        self._on_receive = on_receive
        try:
            self.sock.bind((self.host, self.port))
        except OSError as e:
            self.logger.error(f"Failed to bind to {self.host}:{self.port}: {e}")
            raise
        
        self.running = True
        self.listen_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.listen_thread.start()
        self.logger.info(f"Listening on {self.host}:{self.port}")

    def stop(self):
        self.running = False
        if self.sock:
            self.sock.close()
        if self.listen_thread:
            self.listen_thread.join(timeout=1)

    def send(self, addr: tuple, data: bytes):
        try:
            self.sock.sendto(data, addr)
        except Exception as e:
            self.logger.warning(f"Failed to send data to {addr}: {e}")

    def _listen_loop(self):
        while self.running:
            try:
                data, addr = self.sock.recvfrom(self.buffer_size)
                if self._on_receive:
                    self._on_receive(data, addr)
            except OSError:
                if self.running:
                    self.logger.error("Socket error while receiving")
                break
            except Exception as e:
                self.logger.error(f"Error in listen loop: {e}")

