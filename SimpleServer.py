import socket

HOST, PORT = '', 80

listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
listen_socket.bind((HOST, PORT))
listen_socket.listen(1)
print( 'Serving HTTP on port %d ...' % PORT )

while True:
    client_connection, client_address = listen_socket.accept()
    try:
        request_data = client_connection.recv(1024).decode('utf-8')
        if request_data.find('/status') >= 0 : 
            with open('leiden_status.txt','r') as server:
                http_response = 'HTTP/1.1 200 OK\n\n'
                http_response += server.read()
                client_connection.sendall( http_response.encode('utf-8') )
    except:
        pass
    client_connection.close()