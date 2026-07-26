import socket
def threaded_client(client):
    print(client)
    client.send(b"You are connected.")
    print("Helloworld3")
    while True:
        recieved_data = client.recv(4096)
        print("Helloworld4")
        if not recieved_data:
            print("The client has disconnected.")
            break
        print("Recieved data: ", recieved_data.decode())
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
    print("Helloworld")
    client,addr = s.accept()
    print("Helloworld2")
    threaded_client(client)

