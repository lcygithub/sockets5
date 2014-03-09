#!usr/bin/evn python
#! -*- coding:utf8 -*-
import socket
import base64
import select
import threading
import struct
from encrypt import encrypt, decrypt
import json

# config
fp = file("config.json", "r")
config = json.loads(fp.read())
Remote_addr = config["Remote_server_addr"]
Remote_port = config["Remote_server_port"]


def make_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
    server.bind((Remote_addr, Remote_port))
    server.listen(5)
    return server

def recv_all(conn): 
    datas = []
    while True:
        data = conn.recv(1024)
        if len(data) <= 0:
            break
        datas.append(data)
    return "".join(datas)

def recv_argue(sock, size):
    remain = size
    datas = []
    while remain > 0:
        data = sock.recv(remain)
        if len(data) == 0:
            raise Exception("Connection end")
        remain -= size
        datas.append(data)
    datas = "".join(datas)
    if len(datas) != size:
        raise Exception("recv data error")
    return datas

def connectTarget(conn, tth):
    # \x00\x10 \r www.baidu.com \x00P
    req = conn.recv(1024)
    if len(req) <= 0:
        raise Exception("Haven't recv data")
    req = decrypt(req)
    if len(req[2:]) != struct.unpack(">H", req[0:2])[0]:
        print repr(req)
        return False
        # raise Exception("Recv data error")
    addr_length = ord(req[2])
    target_addr = req[3: addr_length+3]
    target_port = struct.unpack(">H", req[addr_length+3:])[0]
    print "Thread %d"%tth, target_addr, target_port
    target = socket.create_connection((target_addr, target_port))
    return target

def send_all(sock, data):
    bytes_size = 0
    while True:
        res = sock.send(data)
        if res < 0:
            return res
        bytes_size += res
        if bytes_size == len(data):
            return bytes_size

def sofineConnTarget(conn, target):
    try:
        sockset = [conn, target]
        while True:
            r, w, e = select.select(sockset, [], [])
            if conn in r:
                data = decrypt(conn.recv(4096))
                if len(data) <=0 :
                    break
                res = send_all(target, data)
                if res < len(data):
                    raise Exception("Faile to send all data to target")
            if target in r:
                data = encrypt(target.recv(4096))
                if len(data) <= 0:
                    break
                res = send_all(conn, data)
                if res < len(data):
                    raise Exception("Faile to send all data to conn")
    except:
        conn.close()
        target.close()

def sockets5Server(conn, tth):
    target = connectTarget(conn, tth)
    if target:
        sofineConnTarget(conn, target)
    else:
        conn.close()

if __name__ == '__main__':
    server = make_server()
    sockset = [server]
    tth = 0
    while True:
        r,w,e = select.select(sockset, [], [])
        if server in r:
            conn, addr = server.accept()
            tth += 1
            threading.Thread(target=sockets5Server, args=(conn, tth)).start()