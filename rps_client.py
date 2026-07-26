import socket

class player_local():
    def move(self):
        self.choice = input('Please move!')

def main():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect(('localhost', 25585))
    print("Connected to server.")
while True:
    main()
