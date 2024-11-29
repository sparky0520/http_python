import socket
import threading
from multiprocessing import Process
from re import Match, search
from urllib.parse import unquote
import os

PORT = 8081
BUFFER = 104857600  # 100 Megabytes

'''
Create a server socket and configure it

Start Server Loop
Start Accepting connections
On connection create temporary client socket
create a thread to execute the handle_client function
    |
    --- Build HTTP Response Header
    |
    --- Search for file and get file content
    |
    --- Build HTTP Response Body
    |
    --- Send Response and close client socket
'''
def get_mime_type(extension):
    mime_types = {
    # Text Files
    "txt": "text/plain",
    "csv": "text/csv",
    "html": "text/html",
    "htm": "text/html",
    "css": "text/css",
    "js": "application/javascript",
    "json": "application/json",
    "xml": "application/xml",

    # Image Files
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "gif": "image/gif",
    "bmp": "image/bmp",
    "tiff": "image/tiff",
    "ico": "image/vnd.microsoft.icon",
    "svg": "image/svg+xml",
    "webp": "image/webp",

    # Audio Files
    "mp3": "audio/mpeg",
    "wav": "audio/wav",
    "ogg": "audio/ogg",
    "m4a": "audio/mp4",
    "flac": "audio/flac",

    # Video Files
    "mp4": "video/mp4",
    "avi": "video/x-msvideo",
    "mov": "video/quicktime",
    "wmv": "video/x-ms-wmv",
    "flv": "video/x-flv",
    "mkv": "video/x-matroska",
    "webm": "video/webm",
    "3gp": "video/3gpp",
    # Font Files
    "ttf": "font/ttf",
    "otf": "font/otf",
    "woff": "font/woff",
    "woff2": "font/woff2",

    # Arbitrary Type
    "unknown": "application/octet-stream"
    }
    return mime_types.get(extension, mime_types["unknown"])

def get_file_ext(file_path):
    match = search(r'[^.\\/:*?"<>|\r\n]+$',file_path)
    if match:
        extension = match.group()
        return extension
    return ''

def get_file_path(request):
    match : Match= search(r'GET /([^ ]*) HTTP/1',request)
    if match:
        encoded_file_path = match.group(1)  # first capturing group
        file_path = unquote(encoded_file_path) # remove special char format (%xx) with their single char equivalent
        return './'+file_path
    return ''

def client_thread(clientsocket: socket.socket):
    request= clientsocket.recv(BUFFER,0).decode('ASCII')
    # header preparation
    file_path = get_file_path(request)
    print("File Path: ",file_path)
    extension = get_file_ext(file_path)
    print("Extension: "+ extension)
    mime_type = get_mime_type(extension)
    print("Mime Type: "+mime_type)
    # extracting requested file contents
    contents=None
    cur_dir = os.getcwd()
    file= os.path.join(cur_dir, file_path)  # VULNERABILITY : Unrestricted Access to computer by providing absolute path - Relative File Path Prepended with ./ to dodge this (In get_file_path function) 
    print("Absolute File Path: "+ file)
    if (not os.path.exists(file)):
        response = 'HTTP/1.1 404 Not Found\r\nContent-Type: text/plain\r\n\r\n404 Not Found'
    elif(os.path.isdir(file)):
        response = 'HTTP/1.1 403 Forbidden\r\nContent-Type: text/plain\r\n\r\n403 Forbidden'
    else:    
        # We are reading html and other text in binary mode but due to mime type the browser knows how to render it. Hence special characters not printed on the webpage
        with open(file,"rb") as f:
            contents = f.read()
        response = (
            f'HTTP/1.1 200 OK\r\n'
            f'Content-Type: {mime_type}\r\n'
            f'Content-Length: {len(contents)}\r\n'
            f'\r\n'
        )
    # sending response and closing socket
    clientsocket.send(response.encode('ASCII')) # converting string to byte object
    if contents:
        clientsocket.send(contents)
    clientsocket.close() 
    return None

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)   # enable address reuse
server_socket.bind(('', PORT))
server_socket.listen(8)

while True:
    print(f'Server listening on port {PORT}')
    (client_socket, address) = server_socket.accept()

    # Creating and dispatching process
    p = Process(target=client_thread, args=[client_socket])
    p.start()
    p.join()
    # # Creating and dispatching thread
    # ct = threading.Thread(target=client_thread, args=[client_socket])
    # ct.start()