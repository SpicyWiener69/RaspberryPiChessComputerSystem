import socket
import select
import os
import time


class Socket:
    def __init__(self,file_path:str):
        self.sock = None    
        self.file_path = file_path
    
    # Context manager enter
    def __enter__(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET)
        self.sock.setblocking(False)
        try:
            self.sock.connect(self.file_path)
        except BlockingIOError:
            # Non-blocking connect in progress
            pass
        
        return self
    
    # Context  exit
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.sock:
            self.sock.close()
            self.sock = None
        return False
    
    def read_as_str(self) -> str:
        try:
            data = self.sock.recv(1024)
            if data:
                return str(data)
        except BlockingIOError:
            # No data available yet
            pass
        except ConnectionResetError:
            print("Connection closed by server")
        
        return None
            
    # def write(self,message:str):
    #     print(message)
    #     message = message.encode()
    #     self.sock.sendall(message)
    def write(self, message: str):
        buf = message.encode()
        while buf:
            _, writable, _ = select.select([], [self.sock], [])
            if writable:
                sent = self.sock.send(buf)
                buf = buf[sent:]

def wait_unix_socket(path:str, timeout=3.0, interval=0.05, prt = True):
    """
    Waits until UNIX socket at `path` exists with a timeout.
    """
    start = time.time()
    if prt:
        print('looking up file path...')
    while time.time() - start < timeout:
        if not os.path.exists(path):
            time.sleep(interval)
        else:
            if prt:
                print('socket exists')
            return True
    return False


if __name__ == "__main__":
    #worker thread implmentation
    
    if not wait_unix_socket('/tmp/test'):
        exit(1)
        
    with Socket('/tmp/test') as sock:
        while True:
            data  = sock.read_as_str()
            if data:
                sock.write('ff')
            time.sleep(0.1)
        
        # sock = socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET)
        # sock.connect("/tmp/chess_ui_socket")

        