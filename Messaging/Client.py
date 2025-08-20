# If running on two computers,
# replace '127.0.0.1' with server’s LAN IP.
import socket
import threading

# Function to receive messages from server


def receive_messages(client_socket):
    while True:
        try:
            message = client_socket.recv(1024).decode()
            if not message:
                break
            print(f"Server: {message}")
        except:
            print("Connection closed.")
            break

# Function to send messages to server


def send_messages(client_socket):
    while True:
        try:
            message = input("")
            client_socket.send(message.encode())
        except:
            break


def main():
    host = '0.0.0.0'  # server IP (localhost for testing)
    port = 12345

    # socket.AF_INET6 for IPv6 for udp SOCK_DGRAM
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    client_socket.connect((host, port))
    print(f"Connected to server {host}:{port}")

    # Start threads
    t1 = threading.Thread(target=receive_messages, args=(
        client_socket,), daemon=True)
    t2 = threading.Thread(target=send_messages, args=(
        client_socket,), daemon=True)
    t1.start()
    t2.start()
    t1.join()
    t2.join()


if __name__ == "__main__":
    main()
