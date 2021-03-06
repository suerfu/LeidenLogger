# This file will start a simple server to show the status of the Leiden fridge upon HTTP request.
# The request is xxxx.xxxx.xxxx.xxxx/status.

import socket

HOST, PORT = '', 80
    # 80 is the port for http

# Create and configure the socket object.
listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
listen_socket.bind((HOST, PORT))
listen_socket.listen(1)
print( 'Serving HTTP on port %d ...' % PORT )


while True:
    
    # Look for new connections
    client_connection, client_address = listen_socket.accept()
    
    try:
        # Decode the received message.
        # If it asks for status, then print the content of the Leiden status file.
        request_data = client_connection.recv(1024).decode('utf-8')
        
        if request_data.find('/status') >= 0 : 
            with open('leiden_status.txt','r') as server:
                http_response = 'HTTP/1.1 200 OK\n\n'
                http_response += server.read()
                client_connection.sendall( http_response.encode('utf-8') )
                
    except:
        pass
    
    client_connection.close()