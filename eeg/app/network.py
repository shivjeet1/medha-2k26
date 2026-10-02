import socket
from PyQt5.QtCore import QThread, pyqtSignal

class TCPServerThread(QThread):
    # Emits: (ADC_Value, LO_Plus_Status, LO_Minus_Status)
    data_received = pyqtSignal(int, int, int)
    status_update = pyqtSignal(str)

    def __init__(self, host='0.0.0.0', port=5000):
        super().__init__()
        self.host = host
        self.port = port
        self.running = True

    def run(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind((self.host, self.port))
            server.listen(1)
            self.status_update.emit(f"Waiting for ESP8266 on port {self.port}...")
            
            while self.running:
                try:
                    server.settimeout(1.0)
                    conn, addr = server.accept()
                    self.status_update.emit(f"CONNECTED: Connected: {addr[0]}")
                    
                    data_buffer = b""
                    with conn:
                        while self.running:
                            data = conn.recv(1024)
                            if not data:
                                break
                            
                            data_buffer += data
                            while b"\n" in data_buffer:
                                line, data_buffer = data_buffer.split(b"\n", 1)
                                try:
                                    parts = line.decode().strip().split(",")
                                    if len(parts) == 3:
                                        val = int(parts[0])
                                        lo_p = int(parts[1])
                                        lo_m = int(parts[2])
                                        self.data_received.emit(val, lo_p, lo_m)
                                except ValueError:
                                    pass
                                    
                    self.status_update.emit("WARNING: ESP8266 disconnected. Waiting...")
                except socket.timeout:
                    continue
                except Exception as e:
                    self.status_update.emit(f"Error: {e}")

    def stop(self):
        self.running = False
        self.wait()
