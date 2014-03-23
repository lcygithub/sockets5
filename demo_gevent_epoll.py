import socket
import select
import struct
import time
import zlib

SERVER_ADDR = "0.0.0.0"
SERVER_PORT = 1080
EOL1 = "\n\n"
EOL2 = "\n\r\n"
events = []
socks = []
unsocks = []
connections, messages, steps, corresponding, remotes_address, remotes_dict = {}, {}, {}, {}, {}, {}
should_dead = []
epoll = select.epoll()
options = {
    "in": select.EPOLLIN,
    "out": select.EPOLLOUT,
    "both": select.EPOLLIN|select.EPOLLOUT
}
socket_errors= {
     32: 'Broken pipe',
    104: 'Connection reset by peer',
    106: 'Transport endpoint is already connected',
    110: 'Connection timed out',
    114: 'Operation already in progress',
    115: 'Operation now in progress'
 }

def handle_Broken_pipe(conn_fileno=None, remote_fileno=None, error=None):
    pass
def handle_Connection_reset_by_peer(conn_fileno=None, remote_fileno=None, error=None):
    pass
def handle_Transport_endpoint_is_already_connected(conn_fileno=None, remote_fileno=None, error=None):
    pass
def handle_Connection_timed_out(conn_fileno=None, remote_fileno=None, error=None):
    pass
def handle_Operation_already_in_progress(conn_fileno=None, remote_fileno=None, error=None):
    pass
def handle_Operation_now_in_progress(conn_fileno=None, remote_fileno=None, error=None):
    pass

handle_errors = dict([
    (32, handle_Broken_pipe),
    (104, handle_Connection_reset_by_peer),
    (106, handle_Transport_endpoint_is_already_connected),
    (110, handle_Connection_timed_out),
    (114, handle_Operation_already_in_progress),
    (115, handle_Operation_now_in_progress)
])
# def handle_error(conn_fileno, remote_fileno, error):

def global_log():
    print time.time()
    print "connections:", connections
    print "corresponding", corresponding
    # print "messages:", messages
    print "events:", events
    print "steps:", steps
    print "remotes_address", remotes_address
    print "remotes_dict", remotes_dict

def make_corresponding(conn, remote):
    corresponding[conn.fileno()] = remote.fileno()
    corresponding[remote.fileno()] = conn.fileno()

def del_corresponding(conn, remote):
    del corresponding[conn.fileno()]
    del corresponding[remote.fileno()]

def clear_sock(fileno):
    connections[fileno].close()

def epoll_register(sock, opt, remote=False):
    global_log()
    sock.setblocking(0)
    print remote
    print "sock.fileno():", sock.fileno()
    try:
        epoll.register(sock.fileno(), options[opt])
    except IOError, v:
        if v[0] == 17:
            epoll.unregister(sock.fileno())
            epoll.register(sock.fileno(), options[opt])
    connections[sock.fileno()] = sock
    messages[sock.fileno()] = ""
    if not remote:
        steps[sock.fileno()] = 1
    print "new sock add-in:", sock.fileno()

def make_remote(fileno, address):
    try:
        remote = remotes_dict[fileno]
    except KeyError:
        remote = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        remote.setblocking(0)
        remotes_dict[fileno] = remote
        socks.append(remote.fileno())

    try:
        remote.connect(address)
    except socket.error, v:
        print v
        if v[0] == 106:
            return remote
        elif v[0] == 110:
            return False
        else:
            handle_errors[v[0]]()

def make_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((SERVER_ADDR, SERVER_PORT))
    server.listen(5)
    server.setblocking(0)
    connections[server.fileno()] = server
    epoll.register(server.fileno(), select.EPOLLIN)
    print "Server started listen http://0.0.0.0:1080"
    return server

def recv_argue(sock, size):
    remain = size
    datas = ""
    i = 0
    count = 1
    now = time.time()
    while remain > 0:
        try:
            data = sock.recv(remain)
            if len(data) == 0:break
            remain -= len(data)
            datas += data
        except socket.error, e:
            if i == 0:
                print e, sock
                i += 1
    if len(datas) != size:
        print "recv_argue datas:", repr(datas), size
        raise Exception("datas length != size")
    return datas

def write_data(sock, data):
    try:
        fp = sock.makefile("w", 0)
        fp.write(data)
        fp.close()
        return True

    except socket.error, v:
        if v[0] == 32:
            # Broken pipe
            sock_fileno = sock.fileno()
            cor_fileno = corresponding[sock_fileno]
            epoll.modify(sock_fileno, 0)
            epoll.modify(cor_fileno, 0)
            del steps[sock_fileno]

def handle_request(step, fileno):
    if step == 1:
        data = recv_argue(connections[fileno], 3)
        print repr(data)
        steps[fileno] += 1

    elif step == 2:
        global_log()
        print ">>>>>>>>>>>>>>>>>>>>>send to ", fileno
        result = "\x05\x00"
        try:
            write_data(connections[fileno], result)
        except socket.error, v:
            print v
        steps[fileno] += 1

    elif step == 3:
        conn = connections[fileno]
        req = recv_argue(conn, 5)
        if len(req) != 5:
            raise Exception("1.request error")
        if len(req) == 0:
            raise Exception("Connection end.")
        if ord(req[3]) == 1:
            addr_ip = recv_argue(conn, 4)
            addr = socket.inet_ntoa(addr_ip)
        elif ord(req[3]) == 3:
            addr_len = ord(req[4])
            addr = recv_argue(conn, int(addr_len))
        elif ord(req[3]) == 4:
            addr_ip = recv_argue(conn, 16)
            addr = socket.inet_ntop(socket.AF_INET6, addr_ip)
        else:
            raise Exception("addr type not support!")
        port = struct.unpack(">H", recv_argue(conn,2))[0]
        print time.time(),  addr, port
        remotes_address[fileno] = (addr, port)
        steps[fileno] += 1

    elif step == 4:
        remote = make_remote(fileno, remotes_address[fileno])
        conn = connections[fileno]
        if remote:
            epoll_register(remote, "both", True)
            print "add remote", remote
            make_corresponding(conn, remote)
            steps[fileno] += 1

    elif step == 5:
        reply = "\x05\x00\x00\x01"
        reply += socket.inet_aton(SERVER_ADDR) + struct.pack(">H", SERVER_PORT)
        conn = connections[fileno]
        write_data(conn, reply)
        steps[fileno] += 1
        print "write to conn"

    elif step == 6:
        try:
            messages[fileno] += connections[fileno].recv(1024)
            if EOL1 in messages[fileno] or EOL2 in messages[fileno] :
                steps[fileno] += 1
        except socket.error, v:
            handle_errors[v[0]]()

    elif step == 7:
        remote = corresponding[fileno]
        if messages[remote]:
            conn = connections[fileno]
            print "write"
            print repr(messages[remote])
            write_data(conn, messages[remote])
            messages[remote] = ""
        else:
            try:
                remote = corresponding[fileno]
            except KeyError:
                epoll.modify(fileno, 0)
                del steps[fileno]
                print "messages[remote]:", messages[remote]

def main():
    global events
    server = make_server()
    while True:
        # time.sleep(1)
        events = epoll.poll(1)
        global_log()
        for fileno, event in events:
            print "dealing with:", fileno, event
            if fileno == server.fileno():
                conn, addr = server.accept()
                epoll_register(conn, "both")

            elif event & select.EPOLLIN:
                try:
                    step = steps[fileno]
                    handle_request(step, fileno)
                except KeyError:
                    print "messages[fileno]", repr(messages[fileno])
                    if EOL1 not in messages[fileno] and EOL2 not in messages[fileno]:
                        try:
                            data = connections[fileno].recv(1024)
                            messages[fileno] += data
                            print "remote recv datas:", repr(data)
                            if EOL1 in messages[fileno] or EOL2 in messages[fileno]:
                                conn_fileno = corresponding[fileno]
                                print "remote  modify", fileno
                        except socket.error, v:
                            if v[0] == 104:
                                # Connection reset by peer
                                conn_fileno = corresponding[fileno]
                                epoll.modify(fileno, 0)
                    else:
                        should_dead.append(fileno)

            elif event & select.EPOLLOUT:
                try:
                    step = steps[fileno]
                    handle_request(step, fileno)
                except KeyError:
                    remote = connections[fileno]
                    conn = corresponding[fileno]
                    data = messages[conn]
                    write_data(remote, data)

            elif event & select.EPOLLHUP:
                epoll.unregister(fileno)
                unsocks.append(fileno)
                connections[fileno].close()
                del corresponding[fileno]
                del connections[fileno]
                del messages[fileno]

if __name__ == '__main__':
    main()
