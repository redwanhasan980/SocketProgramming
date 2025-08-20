import socket
import threading

# Function to handle receiving messages from the client


def receive_messages(conn):
    while True:
        try:
            message = conn.recv(1024).decode()
            if not message:
                break
            print(f"Client: {message}")
        except:
            print("Connection closed.")
            break

# Function to handle sending messages to the client


def send_messages(conn):
    while True:
        try:
            message = input("")
            conn.send(message.encode())
        except:
            break


def main():
    host = '0.0.0.0'   # special IP address that means “all available network interfaces
    port = 12345

    server_socket = socket.socket(
        socket.AF_INET, socket.SOCK_STREAM)  # UDP (SOCK_DGRAM)
    server_socket.bind((host, port))
    server_socket.listen(1)

    print(f"Server listening on {host}:{port}...")
    conn, addr = server_socket.accept()
    print(f"Connected by {addr}")

    # Start threads for send and receive
    t1 = threading.Thread(target=receive_messages, args=(conn,))
    t2 = threading.Thread(target=send_messages, args=(conn,))
    t1.start()
    t2.start()
    t1.join()
    t2.join()


if __name__ == "__main__":
    main()
