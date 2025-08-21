#!/usr/bin/env python3
import socket
import threading
import os
import json
import struct
from pathlib import Path


class FileServer:
    def __init__(self, host='0.0.0.0', port=8888, storage_dir='server_files'):
        self.host, self.port = host, port
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        self.server_socket = None

    def start(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            print(f"[Server] Running on {self.host}:{self.port}")
            print(f"[Server] Storage: {self.storage_dir.absolute()}")

            while True:
                client_sock, addr = self.server_socket.accept()
                print(f"[Server] Connected: {addr}")
                threading.Thread(target=self.handle_client, args=(
                    client_sock, addr), daemon=True).start()
        except KeyboardInterrupt:
            print("\n[Server] Stopped.")
        except Exception as e:
            print(f"[Server] Error: {e}")
        finally:
            if self.server_socket:
                self.server_socket.close()

    def handle_client(self, sock, addr):
        try:
            while True:
                cmd_data = self.receive_command(sock)
                if not cmd_data:
                    break
                try:
                    # cmd_data is bytes. .decode() (defaults to UTF-8) turns it into a strin
                    command = json.loads(cmd_data.decode())
                    # json.loads(...) converts the JSON string into a Python dict
                    response = self.process_command(command, sock)
                    if response:
                        self.send_response(sock, response)
                except json.JSONDecodeError:
                    self.send_response(
                        sock, {'status': 'error', 'message': 'Invalid command'})
        except Exception as e:
            print(f"[Server] Client {addr} error: {e}")
        finally:
            sock.close()
            print(f"[Server] Disconnected: {addr}")

    def process_command(self, cmd, sock):
        t = cmd.get('type')
        if t == 'list':
            return self.list_files()
        elif t == 'store':
            return self.store_file(cmd, sock)
        elif t == 'delete':
            return self.delete_file(cmd)
        elif t == 'download':
            return self.download_file(cmd, sock)
        return {'status': 'error', 'message': 'Unknown command'}

    def list_files(self):
        try:
            files = [{'name': f.name, 'size': f.stat().st_size}
                     for f in self.storage_dir.iterdir() if f.is_file()]
            return {'status': 'success', 'files': files}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def store_file(self, cmd, sock):
        name, size = os.path.basename(
            cmd.get('filename', '')), cmd.get('size', 0)
        if not name:
            return {'status': 'error', 'message': 'Filename required'}
        path = self.storage_dir / name
        try:
            self.send_response(
                sock, {'status': 'ready', 'message': f"Receiving {name} ({size} bytes)"})
            resp = self.receive_file(sock, path, size)
            self.send_response(sock, resp)
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def receive_file(self, sock, path, size):
        try:
            with open(path, 'wb') as f:
                recvd = 0
                while recvd < size:
                    chunk = sock.recv(min(8192, size-recvd))
                    if not chunk:
                        raise Exception("Transfer lost")
                    f.write(chunk)
                    recvd += len(chunk)
            return {'status': 'success', 'message': f"Stored {path.name}"}
        except Exception as e:
            if path.exists():
                path.unlink()
            return {'status': 'error', 'message': str(e)}

    def delete_file(self, cmd):
        name = os.path.basename(cmd.get('filename', ''))
        if not name:
            return {'status': 'error', 'message': 'Filename required'}
        path = self.storage_dir/name
        if path.exists():
            path.unlink()
            return {'status': 'success', 'message': f"Deleted {name}"}
        return {'status': 'error', 'message': 'File not found'}

    def download_file(self, cmd, sock):
        name = os.path.basename(cmd.get('filename', ''))
        if not name:
            return {'status': 'error', 'message': 'Filename required'}
        path = self.storage_dir/name  # Path(self.storage_dir, name)
        if not path.exists():
            return {'status': 'error', 'message': 'File not found'}
        size = path.stat().st_size
        self.send_response(
            sock, {'status': 'success', 'filename': name, 'size': size})
        self.send_file(sock, path)
        return None

    def send_file(self, sock, path):
        # with statement ensures the file is automatically closed after the block,
        with open(path, 'rb') as f:
            # Reads the file in chunks of 8192 bytes (8 KB) at a time.
            while chunk := f.read(8192):
                sock.sendall(chunk)

    def receive_command(self, sock):
        try:
            length = self.receive_exact(sock, 4)
            if not length:
                return None
            # reads 4 bytes from the socket and converts it into an integer representing the length of the incoming message.
            return self.receive_exact(sock, struct.unpack('!I', length)[0])
        except:
            return None

    def receive_exact(self, sock, n):
        data = b''  # Start with an empty byte string
        while len(data) < n:
            chunk = sock.recv(n-len(data))
            if not chunk:
                break
            data += chunk
        return data

    def send_response(self, sock, resp):
        try:
            data = json.dumps(resp).encode()
            # Converts the length of the JSON data into 4 bytes (network byte order).
            sock.sendall(struct.pack('!I', len(data))+data)
        except:
            pass


if __name__ == "__main__":
    FileServer().start()
