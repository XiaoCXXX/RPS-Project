import socket
from _thread import *

def threaded_client(client):
    print(client)
    client.send(b"You are connected.")
    while True:
        recieved_data = client.recv(4096)
        print("Checking if data is received:")
        if not recieved_data:
            print("The client has disconnected.")
            break
        else: 
            print("data received:\n")
            print(recieved_data)
        print("Recieved data: ", recieved_data.decode())
    print("Closing connection now")
    client.close()
servername = "localhost"
port = 25585
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    s.bind((servername, port))
except socket.error as e:
    print(e)
s.listen()
while True:
    print("Ready to accept the client")
    client,addr = s.accept()
    print("Creating a new thread")
    start_new_thread(threaded_client, (client,))
