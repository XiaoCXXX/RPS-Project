import socket

class player_local():
    def move(self):
        self.choice = input('Please move!')

client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect(('localhost', 25585))
    
def main():
    username = input('Please enter your username: ')
    client_socket.send(username.encode())
    
main()
