#!/usr/bin/env python3
import socket
import json
import struct
from pathlib import Path


class FileClient:
    # 8888 is an unprivileged port, commonly used for development/testing servers.
    def __init__(self, host='localhost', port=8888):
        self.host, self.port = host, port
        self.sock = None

    def connect(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))
            print(f"[Client] Connected {self.host}:{self.port}")
            return True
        except Exception as e:
            print(f"[Client] Connect error: {e}")
            return False

    def disconnect(self):
        if self.sock:
            self.sock.close()
            print("[Client] Disconnected")

    def send_command(self, cmd):
        try:
            data = json.dumps(cmd).encode()
            self.sock.sendall(struct.pack('!I', len(data))+data)
            return True
        except:
            return False

    def receive_response(self):
        try:
            length = self.receive_exact(4)
            if not length:
                return None
            return json.loads(self.receive_exact(struct.unpack('!I', length)[0]).decode())
        except:
            return None

    def receive_exact(self, n):
        data = b''
        while len(data) < n:
            chunk = self.sock.recv(n-len(data))
            if not chunk:
                break
            data += chunk
        return data

    def list_files(self):
        self.send_command({'type': 'list'})
        resp = self.receive_response()
        if not resp:
            return
        if resp['status'] == 'success':
            files = resp.get('files', [])
            if files:
                print("\nFiles:")
                for f in files:
                    print(f"{f['name']:<30}{f['size']:>10} bytes")
            else:
                print("No files")
        else:
            print(f"Error: {resp.get('message')}")

    def store_file(self, local, remote=None):
        path = Path(local)
        if not path.exists():
            print(f"Missing: {local}")
            return
        if not remote:
            remote = path.name
        size = path.stat().st_size
        print(f"[Client] Uploading {remote} ({size} bytes)")
        self.send_command({'type': 'store', 'filename': remote, 'size': size})
        resp = self.receive_response()
        if resp and resp['status'] == 'ready':
            with open(path, 'rb') as f:
                sent = 0
                while chunk := f.read(8192):
                    self.sock.sendall(chunk)
                    sent += len(chunk)
                    if sent % (1024*1024) == 0:
                        print(f"Uploaded {sent}/{size} bytes")
            final = self.receive_response()
            if final:
                print(final['message'])
        else:
            print(f"Error: {resp and resp.get('message')}")

    def delete_file(self, name):
        self.send_command({'type': 'delete', 'filename': name})
        resp = self.receive_response()
        if resp:
            print(resp['message'])

    def download_file(self, remote, local=None):
        if not local:
            local = remote
        path = Path(local)
        self.send_command({'type': 'download', 'filename': remote})
        resp = self.receive_response()
        if not resp:
            return
        if resp['status'] == 'success':
            size = resp['size']
            print(f"[Client] Downloading {remote} ({size} bytes)")
            try:
                with open(path, 'wb') as f:
                    recvd = 0
                    while recvd < size:
                        chunk = self.sock.recv(min(8192, size-recvd))
                        if not chunk:
                            raise Exception("Lost connection")
                        f.write(chunk)
                        recvd += len(chunk)
                print(f"✓ Saved to {path}")
            except Exception as e:
                print(f"Error: {e}")
                if path.exists():
                    path.unlink()
        else:
            print(f"Error: {resp.get('message')}")


def main():
    c = FileClient()
    if not c.connect():
        return
    print(
        "\nCommands: list | store <file> [remote] | delete <name> | download <remote> [local] | quit")
    try:
        while True:
            cmd = input("> ").strip().split()
            if not cmd:
                continue
            if cmd[0] in ('quit', 'exit'):
                break

            elif cmd[0] == 'list':
                c.list_files()
            elif cmd[0] == 'store' and len(cmd) >= 2:
                c.store_file(cmd[1], cmd[2] if len(cmd) > 2 else None)
            elif cmd[0] == 'delete' and len(cmd) >= 2:
                c.delete_file(cmd[1])
            elif cmd[0] == 'download' and len(cmd) >= 2:
                c.download_file(cmd[1], cmd[2] if len(cmd) > 2 else None)
            else:
                print("Unknown command. Type 'help'")
    except KeyboardInterrupt:
        print("\nUse 'quit' to exit")
    finally:
        c.disconnect()


if __name__ == "__main__":
    main()
