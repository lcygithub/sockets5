#!usr/bin/evn python
#! -*- coding:utf8 -*-
import socket
import threading
import struct
import select
from datetime import datetime
import base64

Server_addr = "0.0.0.0"
Server_port = 1080
Server_listen = 5
Auth = False

def make_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # server.setblocking(False)
    server.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)   
    server.bind((Server_addr, Server_port))
    server.listen(5)
    return server

def base64Encrypt(content):
    return base64.encodestring(content)

def base64Decrypt(content):
    return base64.decodestring(content)

def recv_argue(conn, size):
    remain = size
    datas = []
    while remain > 0:
        data = conn.recv(remain)
        if len(data) == 0:
            raise Exception("Connection end.")
        remain -= len(data)
        datas.append(data)
    datas = "".join(datas)
    if len(datas) != size:
        raise Exception("Protocol error")
    return datas

def authenticate(conn, auth):
    req = recv_argue(conn, 3)
    if auth:
        #nedd auth
        conn.send("\x05\x02")
        checkUserPassword(conn)
    else:
        #don't need auth
        conn.send("\x05\x00")
    return conn

def checkUserPassword(conn):
    pass

def handleRemote(conn):
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
    print datetime.now(),  addr, port
    remote = socket.create_connection((addr, port))
    return remote

def handleRequest(conn, remote):
    if remote:
        #success
        reply = "\x05\x00\x00\x01"
    else:
        #faile
        reply = "\x05\x01\x00\x01"
    reply += socket.inet_aton(Server_addr) + struct.pack(">H", Server_port)
    conn.send(reply)
    return conn

def send_all(sock, data):
    bytes_send = 0
    while True:
        res = sock.send(data[bytes_send:])
        if res < 0:
            return res
        bytes_send += res
        if bytes_send == len(data):
            return bytes_send

def sofineConnRemote(conn, remote):
    try:
        sockset = [conn, remote]
        while True:
            r, w, e = select.select(sockset, [], [])
            if conn in r:
                data = conn.recv(4096)
                if len(data) <= 0:
                    break
                res = send_all(remote, data)
                if res < len(data):
                    raise Exception("faile to send all data to remote")

            if remote in r:
                data = remote.recv(4096)
                if len(data) <= 0:
                    break
                res = send_all(conn, data)
                if res < len(data):
                    raise Exception("failed to send all data to conn")
    finally:
        conn.close()
        remote.close()

def sockets5Server(conn, tth):
    conn = authenticate(conn, Auth)
    remote = handleRemote(conn)
    conn = handleRequest(conn, remote)
    sofineConnRemote(conn, remote)

if __name__ == '__main__':
    server = make_server()
    tth = 0
    while True:
        conn, addr = server.accept()
        tth += 1
        threading.Thread(target=sockets5Server, args=(conn, tth)).start()
