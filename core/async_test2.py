import asyncio, socket
import time


class AsyncSocket:
    def __init__(self,file_path):
        self.sock = None    
        self.file_path = file_path
        self.q = asyncio.Queue(maxsize=10)
        
    def __enter__(self):
        #context manager implmentation
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET)
        self.sock.connect(self.file_path)
        self.sock.setblocking(False)
        self.task = asyncio.create_task(self._socket_reader())
    
    def __exit__(self):
        if self.task:
            self.task.cancel()
        if self.sock:
            self.sock.close()
    
    async def _socket_reader(self):
        loop = asyncio.get_running_loop()
        while True:
            data = await loop.sock_recv(self.sock, 1024)
            #end connection
            if not data:
                break
            await self.q.put(data)

    async def poll(self):
        if not self.q.empty():
            data = await self.q.get()
        else:
            return None


