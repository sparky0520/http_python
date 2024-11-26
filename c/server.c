#include <arpa/inet.h>  // network socket address interface - struct
#include <sys/socket.h> // socket functions
#include <stdio.h>      // perror outputs
#include <stdlib.h>     // exit and error codes
#include <pthread.h>    // multi threading
#include <regex.h>      // handle regex ops
#include <string.h>
#include <fcntl.h>
#include <sys/stat.h> // get file stats
#include <unistd.h>   // read, close methods

#define PORT 8080
#define BUFFER_SIZE 104857600 // 100 Megabytes

const char *get_mime_type(const char *file_ext)
{
    if (strcasecmp(file_ext, "html") == 0 || strcasecmp(file_ext, "htm") == 0)
    {
        return "text/html";
    }
    else if (strcasecmp(file_ext, "txt") == 0)
    {
        return "text/plain";
    }
    else if (strcasecmp(file_ext, "jpg") == 0 || strcasecmp(file_ext, "jpeg") == 0)
    {
        return "image/jpeg";
    }
    else if (strcasecmp(file_ext, "png") == 0)
    {
        return "image/png";
    }
    else
    {
        return "application/octet-stream"; // byte stream - unknown data type
    }
}

void build_http_response(const char *file_name, const char *file_ext, char *response, size_t *response_len)
{
    // building http header
    const char *mime_type = get_mime_type(file_ext);
    char *header = (char *)malloc(BUFFER_SIZE * (sizeof(char)));
    snprintf(header, BUFFER_SIZE,
             "HTTP/1.1 200 OK\r\n"
             "Content-Type: %s\r\n"
             "\r\n",
             mime_type);

    // if file doesn't exist, repond with 404 not found
    int file_fd = open(file_name, O_RDONLY);
    if (file_fd == -1)
    {
        snprintf(response, BUFFER_SIZE,
                 "HTTP/1.1 404 Not Found\r\n"
                 "Content-Type: text/plain\r\n"
                 "\r\n"
                 "404 Not Found");
        *response_len = strlen(response);
        return;
    }

    // get file for content length
    struct stat file_stat;
    fstat(file_fd, &file_stat); // put file stats in struct
    off_t file_size = file_stat.st_size;

    // copy header to response buffer
    *response_len = 0;
    memcpy(response, header, strlen(header));
    *response_len += strlen(header);

    // copy file to response buffer
    ssize_t bytes_read;
    while ((bytes_read = read(file_fd, response + *response_len, BUFFER_SIZE - *response_len)) > 0)
    {
        *response_len += bytes_read;
    }
    free(header);
    close(file_fd);
}

// char s[] and char *s differences
// https://media.geeksforgeeks.org/wp-content/uploads/20230914150302/difference-table.png

// char *get_file_extension(const char *name)
// {
//     regex_t regex;
//     regcomp(&regex, "\\.(\\w+)$", 0);
//     regmatch_t matches[2];

//     if (regexec(&regex, name, 2, matches, 0) == 0)
//     {
//         regfree(&regex);
//         char *extension = name + matches[1].rm_so;
//         return extension;
//     }

//     // free compiled regex resources
//     regfree(&regex);
//     return "";
// }

// const char * - data is const
const char *get_file_extension(const char *file_name)
{
    const char *dot = strrchr(file_name, '.'); // returns pointer to last occurence of '.' in file_name. returns NULL if not there.
    if (!dot || dot == file_name)
    {
        return "";
    }
    else
    {
        return dot + 1;
    }
}

char *url_decode(const char *src)
{
    size_t src_len = strlen(src);
    char *decoded = malloc(src_len + 1);
    size_t decoded_len = 0;

    // decoding encoded url for special characters
    for (size_t i = 0; i < src_len; i++)
    {
        if (src[i] == '%' && i + 2 < src_len)
        {
            // there is a special character ascii after % (xx in %xx)
            int hex_val;
            sscanf(src + i + 1, "%2x", &hex_val); // starting after '%'. read next 2 chars (2) and interpret them as hex(x). store in hex_val
            decoded[decoded_len++] = hex_val;
            i += 2;
        }
        else
        {
            decoded[decoded_len++] = src[i];
        }
    }

    decoded[decoded_len] = '\0';
    return decoded;
}

void *handle_client(void *arg)
{
    // conversion of void pointer to int pointer. dereferencing the int pointer to get client_fd
    int client_fd = *((int *)arg);
    char *buffer = (char *)malloc(BUFFER_SIZE * sizeof(char));

    // recieve request data from client and store into buffer
    size_t bytes_recieved = recv(client_fd, buffer, BUFFER_SIZE, 0);
    if (bytes_recieved > 0)
    {

        // check if request is GET
        regex_t regex;
        regcomp(&regex, "^GET /([^ ]*) HTTP/1", REG_EXTENDED); // compiling string for regex use
        regmatch_t matches[2];                                 // we only have one capturing group - ([^ ]*). matches[0] == struct containing start and end index in buffer string for "GET /file.txt HTTP/1" substring, matches[1] == start and end index for "file.txt" in the same.

        // n+1 is the size of matches array to capture the target string + n capture groups
        if (regexec(&regex, buffer, 2, matches, 0) == 0) // if regex matches successfully
        {
            // extract filename from request and decode url
            buffer[matches[1].rm_eo] = '\0'; // cut off buffer from end of file_name - C strings are null-terminated ('\0')
            // points to memory owned by buffer pointer. Hence, this (url_encoded_file_name) should not be independently freed - else double freeing will create undefined behaviour
            const char *url_encoded_file_name = buffer + matches[1].rm_so; // start of file name in buffer (which ends at end of file name)
            char *file_name = url_decode(url_encoded_file_name);

            // get file extension
            char file_ext[32];
            strcpy(file_ext, get_file_extension(file_name));

            // building http response
            char *response = (char *)malloc(BUFFER_SIZE * 2 * sizeof(char));
            size_t response_len;
            build_http_response(file_name, file_ext, response, &response_len);

            // send HTTP response to client
            send(client_fd, response, response_len, 0);

            free(response);
            free(file_name);
        }
        regfree(&regex);
    }

    free(buffer);
    free(arg);
    close(client_fd);
    return NULL;
}

int main(int argc, char *argv[])
{
    // server file descriptor - used to identify the server network socket in the os. allowing the program to reference the socket to send and recieve data over the network
    int server_fd;
    // option to reuse same port after terminating server
    int opt = 1;
    // server network socket address
    struct sockaddr_in server_addr;

    // create a server socket - IPv4 , TCP (instead of UDP)
    if ((server_fd = socket(AF_INET, SOCK_STREAM, 0)) < 0)
    {
        perror("socket failed");
        exit(EXIT_FAILURE);
    }

    if (setsockopt(server_fd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt)) == -1)
    {
        perror("setting socket options failed");
        exit(EXIT_FAILURE);
    }

    // config socket
    server_addr.sin_family = AF_INET;         // IPv4 internet protocol
    server_addr.sin_addr.s_addr = INADDR_ANY; // Taking requests from any internet address
    server_addr.sin_port = htons(PORT);       // Taking requests on port defined in the constant

    // bind file descriptor to socket address (socket to port)
    if ((bind(server_fd, (struct sockaddr *)&server_addr, sizeof(server_addr))) < 0)
    {
        perror("bind failed");
        exit(EXIT_FAILURE);
    }

    // listen for connections
    if (listen(server_fd, 10) < 0)
    {
        perror("listen failed");
        exit(EXIT_FAILURE);
    }

    printf("Server listening on port %d\n", PORT);

    while (1)
    {
        // client network socket address
        struct sockaddr_in client_addr;
        socklen_t client_addr_len = sizeof(client_addr);

        // client file descriptor - used to identify client network socket in the os - allows program to reference and interact with the socket to send and recieve data over a network
        int *client_fd = malloc(sizeof(int)); // in the heap memory to remove limit on data buffer

        // accept client connection
        if ((*client_fd = accept(server_fd, (struct sockaddr *)&client_addr, &client_addr_len)) < 0)
        {
            perror("accepting connection failed");
            continue;
        }

        // create a new thread to handle client request
        pthread_t thread_id;
        // On initialisation, - thread_id thread - will start executing - handle_client function - with - client_fd as argument - (the client to handle).
        pthread_create(&thread_id, NULL, handle_client, (void *)client_fd);
        pthread_detach(thread_id);
    }
}