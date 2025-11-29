#ifndef SOCKET_H
#define SOCKET_H

#ifdef __cplusplus
extern "C" {
#endif

/*callback function when the server recieves stuff, pointer definition*/
typedef void (*server_msg_cb_t)(const char *msg, size_t len, void *user_data);

void socket_send_string(char* buf, int len);
void socket_poll(void);
int server_init(server_msg_cb_t cb, void *user_data);
void server_deinit(void);


#ifdef __cplusplus
} /*extern "C"*/
#endif


#endif 
