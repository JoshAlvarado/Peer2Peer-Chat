import threading
import socket
import sys
import time

server_port = None
connections = {}
timeout = 5
connection_check_interval = 5

def initialize_server():
    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind(('', server_port))
        server_socket.listen(5)
        print("Server is ready and listening on port:", server_port)
        print("Please refer to command 'help' for information and format.")
        threading.Thread(target=check_connections, daemon=True).start()
        while True:
            conn, addr = server_socket.accept()
            threading.Thread(target=handle_client, args=(conn, addr)).start()
    except Exception as e:
        print("Error starting the server:", e)

def check_connections():
    while True:
        for addr in list(connections.keys()):
            try:
                ip, port = addr
                client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                client_socket.connect((ip, int(port)))
                client_socket.getpeername()
                client_socket.close()
            except:
                remove_connection_on_error(addr)
        time.sleep(connection_check_interval)

def handle_client(conn, addr):
    try:
        conn.settimeout(timeout)
        data = conn.recv(1024).decode()
        if data:
            parts = data.split(maxsplit=1)
            command = parts[0]
            args = parts[1] if len(parts) > 1 else ""
            if command == "CONNECT":
                add_connection(addr, args)
            elif command == "TERMINATE":
                remove_connection_directly(addr, args)
            elif command == "MESSAGE":
                port_message_split = args.split(maxsplit=1)
                if len(port_message_split) == 2:
                    sender_port, message = port_message_split
                    display_message((addr[0], sender_port), message)
            elif command == "EXIT":
                remove_connection_directly(addr, args)
    except socket.timeout:
        print(f"Connection with {addr[0]}:{addr[1]} has timed out and been terminated.")
        remove_connection_on_error(addr)
    except socket.error as e:
        print(f"Connection with {addr[0]}:{addr[1]} has been terminated: {e}")
        remove_connection_on_error(addr)
    except Exception as e:
        print(f"Error handling client {addr}: {e}")
    finally:
        conn.close()

def remove_connection_on_error(addr):
    global connections
    connection_tuple = (addr[0], str(addr[1]))
    if connection_tuple in connections:
        connections.pop(connection_tuple)
        print(f"Connection with {addr[0]}:{addr[1]} has been terminated.")

def remove_connection_directly(addr, port=None):
    global connections
    if port is None:
        port = addr[1]
    connection_tuple = (addr[0], str(port))
    if connection_tuple in connections:
        connections.pop(connection_tuple)
        print(f"Connection with {addr[0]}:{port} has been terminated.")
    else:
        print(f"No connection found with {addr[0]}:{port} to remove.")
    list_connections()

def add_connection(addr, port):
    global connections
    if (addr[0], port) not in connections:
        connections[(addr[0], port)] = True
        print(f"\n New connection established from {addr[0]}:{port}")
    list_connections()

def display_message(addr, *message_parts):
    port = addr[1]
    message = ' '.join(message_parts)
    print(f"Message from {addr[0]}:{port} - {message}")

def list_connections():
    print("Current Connections:")
    for idx, (addr, _) in enumerate(connections.items()):
        print(f"{idx + 1}: IP {addr[0]} Port {addr[1]}")

def command_listener():
    while True:
        command = input("\nCommand > ").strip().split()
        if not command:
            continue
        if command[0].lower() == "exit":
            exit_application()
            break
        process_command(command)

def process_command(command):
    if command[0].lower() == "help":
        print_help()
    elif command[0].lower() == "myip":
        print("IP Address:", socket.gethostbyname(socket.gethostname()))
    elif command[0].lower() == "myport":
        print("Listening Port:", server_port)
    elif command[0].lower() == "connect" and len(command) == 3:
        if command[1] == socket.gethostbyname(socket.gethostname()) and int(command[2]) == server_port:
            print("Self connections are not allowed.")
        else:
            initiate_connection(command[1], int(command[2]))
    elif command[0].lower() == "list":
        list_connections()
    elif command[0].lower() == "terminate" and len(command) == 2:
        terminate_connection_by_id(int(command[1]))
    elif command[0].lower() == "send" and len(command) >= 3:
        send_message(int(command[1]), ' '.join(command[2:]))
    else:
        print("Unknown command or incorrect usage. Please refer to command 'help' for commands and command format")

def initiate_connection(ip, port):
    if (ip, str(port)) in [(addr[0], addr[1]) for addr in connections.keys()]:
        print(f"Already connected to {ip}:{port}.")
        return
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((ip, port))
        client_socket.send(f"CONNECT {server_port}".encode())
        client_socket.close()
        connections[(ip, str(port))] = True
        print(f"Connected to {ip}:{port}")
    except Exception as e:
        print(f"Failed to connect to {ip}:{port}: {e}. Please check that the IP and port you are connecting to are valid")

def terminate_connection_by_id(conn_id):
    global connections
    connections_list = list(connections.keys())
    if 0 <= conn_id - 1 < len(connections_list):
        addr = connections_list[conn_id - 1]
        ip, port = addr
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect((ip, int(port)))
            client_socket.send(f"TERMINATE {server_port}".encode())
            client_socket.close()
            remove_connection_directly((ip, int(port)))
        except Exception as e:
            print(f"Error terminating connection with {ip}:{port}: {e}")
    else:
        print("Invalid connection ID")

def send_message(conn_id, message):
    global connections
    connections_list = list(connections.keys())
    if 0 <= conn_id - 1 < len(connections_list):
        addr = connections_list[conn_id - 1]
        ip, port = addr
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect((ip, int(port)))
            full_message = f"MESSAGE {server_port} {message}".encode()
            client_socket.send(full_message)
            client_socket.close()
        except Exception as e:
            print(f"Error sending message to {ip}:{port}: {e}")
            remove_connection_on_error((ip, int(port)))
    else:
        print("Invalid connection ID")

def exit_application():
    print("Exiting application and closing all connections.")
    for addr in list(connections.keys()):
        ip, port = addr
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect((ip, int(port)))
            client_socket.send(f"EXIT {server_port}".encode())
            client_socket.close()
        except Exception as e:
            print(f"Unable to terminate connection with {ip}:{port}: {e}")
    sys.exit(0)

def print_help():
    print("\nAvailable Commands:")
    print("help - Show this help message")
    print("myip - Display the IP address of this machine")
    print("myport - Display the port number this server is listening on")
    print("connect <IP> <Port> - Connect to another server")
    print("list - List all current connections")
    print("terminate <Connection ID> - Terminate a specific connection")
    print("send <Connection ID> <Message> - Send a message to a specific connection")
    print("exit - Close all connections and exit the program")

def get_port_from_user():
    while True:
        try:
            port = int(input("Please enter a valid port number (> 1024): "))
            if port > 1024:
                return port
            else:
                print("Port number must be greater than 1024.")
        except ValueError:
            print("Invalid input. Please enter a numeric value.")

if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1].isdigit():
        server_port = int(sys.argv[1])
    else:
        server_port = get_port_from_user()
    threading.Thread(target=initialize_server, daemon=True).start()
    command_listener() 
