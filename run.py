#!/usr/bin/python3.9

import socketserver, socket
import sys
import time
import _thread, threading
from sdt import DEBUG_PRINT, INFO_PRINT

listen_address, listen_port, remote_address, remote_port = sys.argv[1], \
				int(sys.argv[2]), sys.argv[3], int(sys.argv[4])

threading.stack_size(4096 * 8)

EMPTY_BYTES = bytes()
BUFFER_SIZE = 4096 * 8

try:
    max_active_connections = int(sys.argv[5])
except IndexError:
    max_active_connections = 25

try:
    activity_timeout_seconds = int(sys.argv[6])
except IndexError:
    activity_timeout_seconds = 5


active_connections = 0

class SimpleQueue:

    def __init__(self):
        self.queue = []

    def add(self, thread):
        self.queue.append(thread)

    def pop(self):
        return self.queue.pop(0)

    def __len__(self):
        return len(self.queue)

connection_queue = SimpleQueue()

def queue_manager(queue):
    global active_connections, max_active_connections, connection_queue
    global remote_address, remote_port
    count = 0
    while True:
        if active_connections <= max_active_connections:
            try:
                connection = connection_queue.pop()
                new_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                # Loop that can wait for proxied server to come up
                while True:
                    try:
                        new_socket.connect((remote_address, remote_port))
                        break
                    except ConnectionRefusedError:
                        time.sleep(0.1)
                connection._proxy_socket = new_socket
                connection._activated = True
            except IndexError:
                pass
        count += 1
        if not count % 20:
            DEBUG_PRINT("Active connections, waiting connections",
			active_connections, len(connection_queue))
        time.sleep(0.1)

_thread.start_new_thread(queue_manager, (connection_queue,))

class SimpleHandler(socketserver.StreamRequestHandler):

    def setup(self):
        super().setup()
        self._activated = False

    def handle(self):
        DEBUG_PRINT("Start of handle")
        global EMPTY_BYTES, BUFFER_SIZE
        if not self._activated:
            global connection_queue
            connection_queue.add(self)
        while True:
            if not self._activated:
                time.sleep(0.1)
                continue
            else:
                break
        global active_connections
        active_connections += 1
        count = 0
        quit = 0
        user_s = self.request
        proxy_s = self._proxy_socket
        to_user = to_proxy = EMPTY_BYTES
        last_activity = time.time()
        while True:
            fall_through = False
            try:
                to_proxy = user_s.recv(BUFFER_SIZE, socket.MSG_DONTWAIT)
            except ConnectionResetError:
                quit = 1
            except BlockingIOError:
                pass
            if to_proxy:
                fall_through = True
                last_activity = time.time()
                DEBUG_PRINT("Sending to proxy")
                INFO_PRINT(to_proxy)
                proxy_s.send(to_proxy)
                to_proxy = EMPTY_BYTES
            try:
                to_user = proxy_s.recv(BUFFER_SIZE, socket.MSG_DONTWAIT)
            except ConnectionResetError:
                quit = 1
            except BlockingIOError:
                pass
            if to_user:
                fall_through = True
                last_activity = time.time()
                DEBUG_PRINT("Sending to user")
                INFO_PRINT(to_user)
                user_s.send(to_user)
                to_user = EMPTY_BYTES
            if fall_through:
                continue
            if last_activity + activity_timeout_seconds < time.time():
                quit = 1
            if quit: break
            time.sleep(0.01)
        DEBUG_PRINT("End of handle")

    def finish(self):
        global active_connections
        active_connections -= 1
        super().finish()
        self.request.close()
        self._proxy_socket.close()

class SimpleTCPProxy(socketserver.ThreadingMixIn, socketserver.TCPServer):

    daemon_threads = True

    def __init__(self):
        global listen_address, listen_port
        socketserver.TCPServer.__init__(self, (listen_address, listen_port),
					SimpleHandler)

    def serve_forever(self, *arguments, **keywords):
        try:
            super().serve_forever(*arguments, **keywords)
        finally:
            self.socket.close()
            #self.socket.shutdown(socket.SHUT_RDWR)

server = SimpleTCPProxy()
server.server_activate()
server.serve_forever()
