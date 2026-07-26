import socket
def threaded_client(client):
    client.send(b"You are connected.")
    while True:
        recieved_data = client.recv(64)
        if not recieved_data:
            print("The client has disconnected.")
            break
        print("Recieved data: ", recieved_data.decode())
servername = "localhost"
port = 25585
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    s.bind((servername, port))
except:
    exit("ERROR: Port is occupied")
while True:
    s.listen()
    #print("Helloworld")
    client,addr = s.accept()
    threaded_client(client)

