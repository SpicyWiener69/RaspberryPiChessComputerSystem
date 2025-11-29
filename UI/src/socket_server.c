#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <errno.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <fcntl.h>


#include "socket_server.h"

#define SOCKET_NAME "/tmp/chess_ui_socket"
#define BUFFER_SIZE 1024
//#define POLL_INTERVAL_MS 50

//static lv_obj_t *g_board_cont = NULL;
static int listen_fd = -1;
static int client_fd = -1;

static server_msg_cb_t self_cb;
static void* self_cb_data;
/* LVGL renderer */
//void draw_fen(const char *fen, lv_obj_t *cont);

/* set fd non-blocking */
static int set_nonblocking(int fd) {
    int flags = fcntl(fd, F_GETFL, 0);
    if (flags == -1) return -1;
    return fcntl(fd, F_SETFL, flags | O_NONBLOCK);
}

void socket_send_string(char* buf, int len){
    send(client_fd, buf, len, 0);
}

void socket_poll(void) {
    char buf[BUFFER_SIZE];
    /* 1) Accept new client if none */
    if (client_fd == -1) {
        int new_fd = accept(listen_fd, NULL, NULL);
        if (new_fd != -1) {
            client_fd = new_fd;
            set_nonblocking(client_fd);
        } else if (errno != EAGAIN && errno != EWOULDBLOCK) {
            perror("accept");
        }
    }

    if (client_fd != -1) {
        ssize_t n = recv(client_fd, buf, sizeof(buf)-1, 0);
        if (n > 0) {
            buf[n] = '\0';
            if (self_cb) {
                fprintf(stdout,"size:%ld\n",n);
                self_cb(buf, (size_t)n, self_cb_data);
            }
        } else if (n == 0) {
            /* client closed */
            close(client_fd);
            client_fd = -1;
        } else if (errno != EAGAIN && errno != EWOULDBLOCK) {
            perror("recv");
            close(client_fd);
            client_fd = -1;
        }
    }
}

int server_init(server_msg_cb_t cb,void* user_data) {
    self_cb = cb;
    self_cb_data = user_data;
    unlink(SOCKET_NAME);

    listen_fd = socket(AF_UNIX, SOCK_SEQPACKET, 0);
    if (listen_fd == -1) return -1;

    struct sockaddr_un addr;
    memset(&addr, 0, sizeof(addr));
    addr.sun_family = AF_UNIX;
    strncpy(addr.sun_path, SOCKET_NAME, sizeof(addr.sun_path)-1);
    
    if (bind(listen_fd, (struct sockaddr *)&addr, sizeof(addr)) == -1) return -1;
    if (listen(listen_fd, 1) == -1) return -1;
    if (set_nonblocking(listen_fd) == -1) return -1;
    return 0;
}

void server_deinit(void) {
    if (client_fd != -1) close(client_fd);
    if (listen_fd != -1) close(listen_fd);
    unlink(SOCKET_NAME);
}