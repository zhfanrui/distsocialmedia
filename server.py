# Import the required libraries
from socket import *
import os
import json
import time
import threading
import datetime

class API(object):
    """
    This class contains all the functions to achieve the system.
    This class should be run in single-instance mode.
    This API are designed trying to follow RESTful API regulation.
        - post[Noun]: change the data of [Noun]
        - get[Noun]:  get the data of [Noun]
    """
    def __init__(self):
        super(API, self).__init__()

    def postStatus(self, args, addr):
        """
            Change my current status
        """
        status = args.split("=")[1]
        jsonObj = None
        with open("status.json", 'r+') as f:
            content = f.read()
            if content == "":
                jsonObj = []
            else:
                jsonObj = json.loads(content)
            tmpobj = {"timestamps": time.time(), "status": status, "like": []}
            jsonObj.append(tmpobj)
        with open("status.json", 'w') as f:
            f.write(json.dumps(jsonObj))
        return "HTTP/1.1 200 OK\r\n\r\nUpdate succeed!"

    def getStatus(self, args, addr):
        """
            Get my current status if ip is my friend
        """
        with open("friends.json", 'r') as f:
            jsonObj = json.loads(f.read())
            for i in jsonObj:
                if i['ip'] == addr[0]:
                    with open("status.json", 'r') as g:
                        return "HTTP/1.1 200 OK\r\n\r\n" + g.read()
        return "HTTP/1.1 401 Unauthorized\r\n\r\n<h1>He or she is not your friend.</h1>"

    def getFriendsStatus(self, args, addr):
        """
            Get all my friends' status
        """
        with open("friends.json", 'r') as f:
            jsonObj = json.loads(f.read())
            returnJson = "<h1>Friends Status</h1>"
            for i in jsonObj:
                tmpsocket = socket(AF_INET,SOCK_STREAM)
                print("[Visiting]: " + ":".join([i['ip'],i['port']]))
                tmpsocket.connect((i['ip'],int(i['port'])))
                tmpsocket.send("GET /api/Status HTTP/1.1\r\n\r\n".encode())
                tmpresponse = tmpsocket.recv(1024)
                headers = tmpresponse.decode("utf-8").split("\r\n")
                httpStatusCode =headers[0].split(" ")[1]
                if httpStatusCode == "200":
                    jsonObj = json.loads(headers[-1])
                    returnJson += "<h2>" + i['name'] + "</h2><ul><li>" + datetime.datetime.fromtimestamp(jsonObj[-1]['timestamps']).strftime('%Y-%m-%d %H:%M:%S') + "</li><li>" + jsonObj[-1]['status'] + "</li><li><button onclick=\"like(\'" + i['ip'] + "\'," + i['port'] + "," + str(jsonObj[-1]['timestamps']) + ");\">Like</button></li><li>"
                    for j in jsonObj[-1]['like']:
                        returnJson += j + ", "
                    returnJson += "</li>"
                else:
                    return tmpresponse + "<p>ip: " + i['ip'] + "</p>"
            return "HTTP/1.1 200 OK\r\n\r\n" + returnJson

    def postLike(self, args, addr):
        """
            Add my status a like
        """
        args = args.split("=")[1]
        with open("friends.json", 'r') as f:
            jsonObj = json.loads(f.read())
            for i in jsonObj:
                if i['ip'] == addr[0]:
                    jsonObj2 = None
                    with open("status.json", 'r') as g:
                        jsonObj2 = json.loads(g.read())
                        for j in jsonObj2:
                            if args == str(j['timestamps']):
                                if addr[0] in j['like']:
                                    return "HTTP/1.1 200 OK\r\n\r\nYou have already liked."
                                else:
                                    j['like'].append(addr[0])
                    with open("status.json", 'w') as g:
                        g.write(json.dumps(jsonObj2))
                    return "HTTP/1.1 200 OK\r\n\r\nSucceed! Please Refresh."
        return "HTTP/1.1 401 Unauthorized\r\n\r\nFailed! He or she is not your friend."

    def postFriendsLike(self, args, addr):
        """
            Add friends' status a like
        """
        args = args.split("&")
        tmpsocket = socket(AF_INET,SOCK_STREAM)
        tmpsocket.connect((args[0].split("=")[1], int(args[1].split("=")[1])))
        tmpsocket.send(("POST /api/Like HTTP/1.1\r\n\r\ntimestamps=" + args[2].split("=")[1]).encode())
        tmpresponse = tmpsocket.recv(1024)
        headers = tmpresponse.decode("utf-8").split("\r\n")
        httpStatusCode =headers[0].split(" ")[1]
        if httpStatusCode == "200":
            return tmpresponse.decode()
        else:
            return tmpresponse + "<p>ip: " + i['ip'] + "</p>"



def httpLink(connectionSocket, addr):
    # Retrieve the message sent by the client
    request = connectionSocket.recv(1024)

    if request == b"":
        # print("Waiting Time Out.")
        return

    # Get the request file name in header
    headers = request.decode("utf-8").split("\r\n")
    method = headers[0].split(" ")[0].lower()
    filename = headers[0].split(" ")[1]
    print(headers)

    # if requests is api
    if "/api/" in filename:
        if method == 'get':
            actionWithArgs = filename.split('/')[-1].split('?')
            action = method + actionWithArgs[0]
            args = actionWithArgs[1] if len(actionWithArgs) > 1 else ""
        elif method == 'post':
            action = method + filename.split('/')[-1]
            args = headers[-1]
        result = getattr(api, action)(args, addr)
        # print(result)
        connectionSocket.send(result.encode())
        # Close the connection
        connectionSocket.close()
        return

    # if requests is root page
    elif filename[-1] == "/":
        filename = filename + "update.html"

    # if requests is normal files
    # if file not found return 404
    if not os.path.isfile("." + filename):
        connectionSocket.send("HTTP/1.1 404 Not Found\r\n\r\n".encode())

    # if file found return 200
    else:
        connectionSocket.send("HTTP/1.1 200 OK\r\n\r\n".encode())

        # return the file contents especially for image format and text/html format
        filecontent = None
        if filename.endswith(".jpg") or filename.endswith(".jpge") or filename.endswith(".png") or filename.endswith(".gif"):
            with open("." + filename, "rb") as f:
                filecontent = f.read()
        else:
            with open("." + filename, "r") as f:
                filecontent = f.read().encode()

        connectionSocket.send(filecontent)

    # Close the connection
    connectionSocket.close()

# Create a single instance of API
api = API()

# Listening port for the server
serverPort = 8088

# Create the server socket object
serverSocket = socket(AF_INET,SOCK_STREAM)

# Bind the server socket to the port
serverSocket.bind(('',serverPort))

# Start listening for new connections
serverSocket.listen(5)

print('The server is ready to receive messages')


while 1:
    # Accept a connection from a client
    sock, addr = serverSocket.accept()
    print(addr)
    # Create a new thread for a client
    t = threading.Thread(target=httpLink, args=(sock, addr))
    t.start()


