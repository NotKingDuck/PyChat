import socket
import threading
from datetime import datetime
import os

# Server class
class ChatServer:
    def __init__(self, host="0.0.0.0", port=12345):
        self.host = host
        self.port = port
        self.clients = {}  # Map of sockets to usernames
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def start(self):
        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            print(f"PyChat Server started on {self.host}:{self.port}")

            threading.Thread(target=self.command_input, daemon=True).start()

            while True:
                client_socket, client_address = self.server_socket.accept()
                print(f"New connection: {client_address[0]}:{client_address[1]}")
                threading.Thread(target=self.handle_client, args=(client_socket, client_address)).start()
        except Exception as e:
            print(f"Error starting server: {e}")
        finally:
            self.server_socket.close()

    def handle_client(self, client_socket, client_address):
        try:
            client_socket.send("Enter your username: ".encode("utf-8"))
            username = client_socket.recv(1024).decode("utf-8").strip()
            if not username:
                username = f"User-{client_address[1]}"
            self.clients[client_socket] = username

            welcome_message = f"Welcome to PyChat, {username}!"
            client_socket.send(welcome_message.encode("utf-8"))
            self.broadcast(f"{username} has joined the chat!", None)

            while True:
                message = client_socket.recv(1024).decode("utf-8")
                if not message:
                    break

                if message.startswith("!"):
                    self.handle_command(message, client_socket, client_address)
                    continue

                log_message = f"[{self.get_timestamp()}] {username}: {message}"
                print(log_message)  # Log the message on the server side
                self.broadcast(log_message, client_socket)
        except ConnectionResetError:
            pass
        except Exception as e:
            print(f"Error handling client {client_address}: {e}")
        finally:
            username = self.clients.pop(client_socket, "Unknown")
            print(f"Connection closed: {client_address[0]}:{client_address[1]}")
            self.broadcast(f"{username} has left the chat.", None)
            client_socket.close()

    def broadcast(self, message, sender_socket):
        to_remove = []
        for client_socket in self.clients.keys():
            if client_socket != sender_socket:
                try:
                    client_socket.send(message.encode("utf-8"))
                except Exception as e:
                    print(f"Error sending message to a client: {e}")
                    to_remove.append(client_socket)
        # Remove clients that encountered errors
        for sock in to_remove:
            self.clients.pop(sock, None)

    def handle_command(self, command, client_socket, client_address):
        username = self.clients.get(client_socket, "Unknown")
        if command == "!clear":
            try:
                client_socket.send("\033c".encode("utf-8"))  # ANSI clear screen
            except Exception as e:
                print(f"Error clearing screen for {username}: {e}")
        elif command == "!exit":
            self.clients.pop(client_socket, None)
            self.broadcast(f"{username} has left the chat.", None)
            client_socket.close()
        elif command == "!commands":
            commands = "\nServer commands:\n!kick [username or IP] - Kick a user from the chat\n!clear - Clear the server console\n!msg [message] - Broadcast a message as the server\n!listpeople - List all connected users\n!commands - List all server commands"
            client_socket.send(commands.encode("utf-8"))
        elif command == "!listpeople":
            user_list = "\nConnected users:\n" + "\n".join(self.clients.values())
            client_socket.send(user_list.encode("utf-8"))
        elif command.startswith("!kick"):
            parts = command.split()
            if len(parts) < 2:
                client_socket.send("Usage: !kick [username or IP]".encode("utf-8"))
                return

            target = parts[1]
            to_kick = None
            for sock, name in self.clients.items():
                if name == target or str(sock.getpeername()[0]) == target:
                    to_kick = sock
                    break

            if to_kick:
                kicked_user = self.clients.pop(to_kick, "Unknown")
                self.broadcast(f"{kicked_user} has been kicked from the server.", None)
                to_kick.close()
            else:
                client_socket.send("User not found.".encode("utf-8"))

    def command_input(self):
        while True:
            command = input()
            if command.startswith("!"):
                if command.startswith("!kick"):
                    parts = command.split()
                    if len(parts) < 2:
                        print("Usage: !kick [username or IP]")
                        continue

                    target = parts[1]
                    to_kick = None
                    for sock, name in self.clients.items():
                        if name == target or str(sock.getpeername()[0]) == target:
                            to_kick = sock
                            break

                    if to_kick:
                        kicked_user = self.clients.pop(to_kick, "Unknown")
                        self.broadcast(f"{kicked_user} has been kicked from the server.", None)
                        to_kick.close()
                        print(f"Kicked {kicked_user}.")
                    else:
                        print("User not found.")
                elif command == "!clear":
                    os.system("cls" if os.name == "nt" else "clear")
                elif command.startswith("!msg"):
                    parts = command.split(" ", 1)
                    if len(parts) < 2:
                        print("Usage: !msg [message]")
                        continue
                    self.broadcast(f"Server: {parts[1]}", None)
                elif command == "!commands":
                    commands = "\nServer commands:\n!kick [username or IP] - Kick a user from the chat\n!clear - Clear the server console\n!msg [message] - Broadcast a message as the server\n!listpeople - List all connected users\n!commands - List all server commands"
                    print(commands)
                elif command == "!listpeople":
                    user_list = "\nConnected users:\n" + "\n".join(self.clients.values())
                    print(user_list)
                else:
                    print("Unknown command.")

    @staticmethod
    def get_timestamp():
        return datetime.now().strftime("%H:%M:%S")

# Client class
class ChatClient:
    def __init__(self, server_ip, server_port):
        self.server_ip = server_ip
        self.server_port = server_port
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.username = None
        self.chat_history = []

    def start(self):
        try:
            self.client_socket.connect((self.server_ip, self.server_port))
            print("Connected to PyChat Server!")

            self.username = input("Enter your username: ").strip()
            self.client_socket.send(self.username.encode("utf-8"))

            threading.Thread(target=self.receive_messages, daemon=True).start()

            self.display_chat_history(clear_screen=True)

            while True:
                message = input()
                if message.startswith("!"):
                    self.client_socket.send(message.encode("utf-8"))
                    if message == "!exit":
                        break
                else:
                    timestamped_message = f"[{self.get_timestamp()}] {self.username}: {message}"
                    self.chat_history.append(timestamped_message)
                    self.display_chat_history(clear_screen=True)
                    self.client_socket.send(message.encode("utf-8"))
        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            self.client_socket.close()

    def receive_messages(self):
        while True:
            try:
                message = self.client_socket.recv(1024).decode("utf-8")
                if message and not message.startswith("Enter your username:"):
                    self.chat_history.append(message)
                    self.display_chat_history(clear_screen=True)
                elif not message:
                    break
            except Exception as e:
                print(f"Error receiving message: {e}")
                break

    def display_chat_history(self, clear_screen=False):
        if clear_screen:
            os.system("cls" if os.name == "nt" else "clear")
        for message in self.chat_history:
            print(message)

    @staticmethod
    def get_timestamp():
        return datetime.now().strftime("%H:%M:%S")

if __name__ == "__main__":
    print("Welcome to PyChat!")
    print("Choose an option:")
    print("1. Start server")
    print("2. Connect as client")

    mode = input("Enter your choice (1/2): ").strip()
    if mode == "1":
        port = int(input("Enter port to run the server on: "))
        server = ChatServer(port=port)
        os.system("cls" if os.name == "nt" else "clear")
        server.start()
    elif mode == "2":
        server_ip = input("Enter server IP: ").strip()
        server_port = int(input("Enter server port: "))
        client = ChatClient(server_ip, server_port)
        
        client.start()
    else:
        print("Invalid choice. Exiting PyChat.")
