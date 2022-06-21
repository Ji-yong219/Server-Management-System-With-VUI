import socketserver

# class ListenerServer(socketserver.ThreadingTCPServer):
class ListenerServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    def __init__(self, host_port_tuple, streamhandler, Controllers):
        super().__init__(host_port_tuple, streamhandler)
        self.linux_connect_dict = Controllers
    pass