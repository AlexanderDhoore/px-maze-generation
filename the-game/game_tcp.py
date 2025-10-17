# game_tcp.py
import asyncio
import socket
import threading

PORT = 1337
QUEUE_MAX = 3


class GameTcp:
    def __init__(self):
        self.clients = {}  # writer => Queue[bytes]
        self.loop = None
        self.thread = threading.Thread(target=self.run_thread, daemon=True)

    def start(self):
        self.thread.start()

    def send(self, payload: bytes | str):
        if isinstance(payload, str):
            payload = payload.encode()
        self.loop.call_soon_threadsafe(self.send_nowait, payload)

    def send_nowait(self, payload: bytes):
        for queue in self.clients.values():
            try:
                queue.put_nowait(payload)
            except asyncio.QueueFull:
                print("Client queue full")

    async def handle_client(self, _, writer: asyncio.StreamWriter):
        print("Client connected")
        sock = writer.get_extra_info("socket")
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

        queue = asyncio.Queue(maxsize=QUEUE_MAX)
        self.clients[writer] = queue
        try:
            while True:
                msg = await queue.get()
                writer.write(msg)
                await writer.drain()
        except Exception:
            pass
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass
            del self.clients[writer]
            print("Client closed")

    async def run_server(self):
        server = await asyncio.start_server(self.handle_client, "0.0.0.0", PORT)
        async with server:
            await server.serve_forever()  # never returns

    def run_thread(self):
        print(f"TCP thread started")
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_until_complete(self.run_server())
        finally:
            self.loop.close()
