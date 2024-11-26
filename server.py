import socket
import threading
from re import Match, search
from urllib.parse import unquote
import os

PORT = 8081
BUFFER = 104857600

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

    # Document Files
    "pdf": "application/pdf",
    "doc": "application/msword",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xls": "application/vnd.ms-excel",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "ppt": "application/vnd.ms-powerpoint",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",

    # Compressed Files
    "zip": "application/zip",
    "rar": "application/vnd.rar",
    "7z": "application/x-7z-compressed",
    "tar": "application/x-tar",
    "gz": "application/gzip",
    "bz2": "application/x-bzip2",

    # Binary and Executable Files
    "exe": "application/vnd.microsoft.portable-executable",
    "bin": "application/octet-stream",
    "dll": "application/vnd.microsoft.portable-executable",

    # Font Files
    "ttf": "font/ttf",
    "otf": "font/otf",
    "woff": "font/woff",
    "woff2": "font/woff2",
    }
    if(extension in mime_types):
        return mime_types[extension]
    else:
        return "application/octet-stream"

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
        return file_path
    return ''

def client_thread(clientsocket: socket.socket):
    request= clientsocket.recv(BUFFER,0)
    
    # header preparation
    file_path = get_file_path(str(request))
    extension = get_file_ext(file_path)
    mime_type = get_mime_type(extension)
    
    # extracting requested file contents
    cur_dir = os.getcwd()
    file= os.path.join(cur_dir, file_path)
    try:
        with open(file) as f:
            contents = f.read()
        response = f'HTTP/1.1 200 OK\r\nContent-Type: {mime_type}\r\nContent-Length: {len(contents)}\r\n\r\n{contents}'
    except:
        response = 'HTTP/1.1 404 Not Found\r\nContent-Type: text/plain\r\n\r\n404 Not Found'

    # sending response and closing socket
    clientsocket.send(response.encode('ASCII')) # converting string to byte object
    clientsocket.close()
    return None

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)   # enable address reuse
server_socket.bind(('', PORT))
server_socket.listen(8)

while True:
    print(f'Server listening on port {PORT}')
    (client_socket, address) = server_socket.accept()
    ct = threading.Thread(target=client_thread, args=[client_socket])
    ct.start()