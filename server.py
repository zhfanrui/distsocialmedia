# Import the required libraries
from socket import *
import os
import json
# import time
import threading
import datetime, calendar
import base64

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

    def postStatus(self, args, addr, cache):
        """
            Change my current status
        """
        status = args.split("=")[1]
        jsonObj = None

        # create status file if it doesn't exist
        if not os.path.isfile("status.json"):
            with open("status.json", 'w') as f:
                pass

        # read status file to get posted status
        with open("status.json", 'r') as f:
            content = f.read()
            if content == "":
                jsonObj = []
            else:
                jsonObj = json.loads(content)

            # add new status to the json object
            tmpobj = {"timestamps": calendar.timegm(datetime.datetime.utcnow().timetuple()), "status": status, "like": []}
            jsonObj.append(tmpobj)

        # convert the json object to file
        # Lock is required
        writelock.acquire()
        with open("status.json", 'w') as f:
            f.write(json.dumps(jsonObj))
        writelock.release()
        return "HTTP/1.1 200 OK\r\n\r\nUpdate succeed!"

    def getStatus(self, args, addr, cache):
        """
            Test modified time and get my current status and profile image if client is my friend
        """

        # get last modified time from header
        modifiedTime = cache.split(": ")[1].split(", ")[1]
        modifiedTime = calendar.timegm(datetime.datetime.strptime(modifiedTime, "%d %b %y %H:%M:%S %Z").timetuple())
        print("[Modified Time] ", modifiedTime)
        with open("friends.json", 'r') as f:
            jsonObj = json.loads(f.read())
            for i in jsonObj:
                if i['ip'] == addr[0]:

                    # get files' last modified time
                    modifiedTimeStatus = calendar.timegm(datetime.datetime.utcfromtimestamp(os.path.getmtime("status.json")).timetuple())
                    modifiedTimeProfile = calendar.timegm(datetime.datetime.utcfromtimestamp(os.path.getmtime("profile.ico")).timetuple())
                    print("[status modified time] ", modifiedTimeStatus)
                    if modifiedTimeStatus > modifiedTime or modifiedTimeProfile > modifiedTime:
                        with open("status.json", 'r') as g:
                            with open("profile.ico", "rb") as h:
                                image64 = base64.b64encode(h.read()).decode("utf-8")
                                return "HTTP/1.1 200 OK\r\n\r\n" + g.read() + "&" + image64
                    else:
                        return "HTTP/1.1 304 Not Modified\r\n\r\n"
        return "HTTP/1.1 401 Unauthorized\r\n\r\n<h1>He or she is not your friend.</h1>"

    def getFriendsStatus(self, args, addr, cache):
        """
            Pass modified time and get all my friends' status
        """

        # if no cache, set last modified time to timestamps 0
        modifiedTime = datetime.datetime.utcfromtimestamp(0).strftime('%a, %d %b %y %H:%M:%S GMT') if cache == "" else cache.split(": ")[1]

        returnJson = ""

        # if full text need to be responded or not
        returnAllTextFlag = 0
        with open("friends.json", 'r') as f:
            jsonObj = json.loads(f.read())
            for i in jsonObj:

                # create a client socket to request status with If-Modified-Since header
                tmpsocket = socket(AF_INET,SOCK_STREAM)
                tmpresponse = b""
                headers = []
                httpStatusCode = 0

                # handle bad connection
                try:
                    tmpsocket.connect((i['ip'],int(i['port'])))
                    tmpsocket.send(("GET /api/Status HTTP/1.1\r\nIf-Modified-Since: " + modifiedTime + "\r\n\r\n").encode())
                    while True:
                        stream = tmpsocket.recv(1024)
                        if len(stream) > 0:
                            tmpresponse += stream
                        else:
                            break

                except:
                    # create a fake response if friend's server is off-line
                    tmpresponse = "HTTP/1.1 503 Service Unavailable\r\n\r\n".encode()

                headers = tmpresponse.decode("utf-8").split("\r\n")
                httpStatusCode = headers[0].split(" ")[1]

                # If httpStatusCode is 200, the status has been changed since last modified time. So, new html need to be responded.
                if httpStatusCode == "200":

                    returnAllTextFlag = 1

                    # backup status and image
                    with open("tmp/"+i['ip']+"_"+i['port'], 'w') as f:
                        f.write(headers[-1])

                # If httpStatusCode is 304, my friend i didn't change the status. And read the status from server cache.
                # If httpStatusCode is 503, my friend i didn't on-line. And read the status from server cache.
                elif httpStatusCode == "304" or httpStatusCode == "503":
                    with open("tmp/"+i['ip']+"_"+i['port'], 'r') as f:
                        headers = [f.read()]

                else:
                    # return an 401 error response immediately because there is some problem with friends.json
                    return tmpresponse + "<p>ip: " + i['ip'] + "</p>"

                # generate html code (it should be better to return a json format)
                statusAndImage = headers[-1].split("&")
                jsonObj = json.loads(statusAndImage[0])
                returnJson += "<h2>" + i['name'] + "</h2><ul><li><img src=\"data:image/ico;base64," + statusAndImage[1] + "\"</li><li>" + datetime.datetime.fromtimestamp(jsonObj[-1]['timestamps']).strftime('%Y-%m-%d %H:%M:%S') + "</li><li>" + jsonObj[-1]['status'] + "</li><li><button onclick=\"like(\'" + i['ip'] + "\'," + i['port'] + "," + str(jsonObj[-1]['timestamps']) + ");\">Like</button></li><li>"
                returnJson += str(len(jsonObj[-1]['like'])) + " likes: "
                returnJson += ", ".join(jsonObj[-1]['like'])
                returnJson += "</li>"

            if returnAllTextFlag:
                return "HTTP/1.1 200 OK\r\n\r\n" + returnJson
            else:
                return "HTTP/1.1 304 Not Modified\r\n\r\n"

    def postLike(self, args, addr, cache):
        """
            Add my status a like
        """
        args = args.split("=")[1]
        with open("friends.json", 'r') as f:
            jsonObj = json.loads(f.read())
            for i in jsonObj:
                # check client is my friend or not
                if i['ip'] == addr[0]:
                    jsonObj2 = None
                    with open("status.json", 'r') as g:
                        jsonObj2 = json.loads(g.read())
                        for j in jsonObj2:
                            # write ip address to certain status
                            if args == str(j['timestamps']):
                                # check duplication
                                if addr[0] in j['like']:
                                    return "HTTP/1.1 200 OK\r\n\r\nYou have already liked."
                                else:
                                    j['like'].append(addr[0])
                    # write-lock is required
                    writelock.acquire()
                    with open("status.json", 'w') as g:
                        g.write(json.dumps(jsonObj2))
                    writelock.release()
                    return "HTTP/1.1 200 OK\r\n\r\nSucceed!"
        return "HTTP/1.1 401 Unauthorized\r\n\r\nFailed! He or she is not your friend."

    def postFriendsLike(self, args, addr, cache):
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
            # handle invalid friends
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

    # Get If-Modified-Since in the header
    modifiedTime = ""
    for i in headers:
        if i.startswith("If-Modified-Since"):
            modifiedTime = i
            break
    print("[header] ", headers[0])
    print("[ModifiedTime] ", modifiedTime)

    # if requests is api
    if "/api/" in filename:
        if method == 'get':
            actionWithArgs = filename.split('/')[-1].split('?')
            action = method + actionWithArgs[0]
            args = actionWithArgs[1] if len(actionWithArgs) > 1 else ""
        elif method == 'post':
            action = method + filename.split('/')[-1]
            args = headers[-1]
        result = getattr(api, action)(args, addr, modifiedTime)
        # print("[return] ", result)
        connectionSocket.send(result.encode())
        # Close the connection
        connectionSocket.close()
        return

    # if requests is root page
    if filename == "/":
        filename = "/update.html"

    # access the friends.html
    if filename == "/friends.html":
        # generate dynamic friends.html first
        result = getattr(api, "getFriendsStatus")("", addr, modifiedTime).split("\r\n\r\n")
        # if something changed, i.e. return the page content with Last-Modified header
        if result[0] == "HTTP/1.1 200 OK":
            filecontent = ""
            # open template file
            with open("friends.template", "r") as f:
                filecontent = f.read().replace("{{data}}", result[1])
            nowTimeStr = datetime.datetime.utcnow().strftime("%a, %d %b %y %H:%M:%S GMT")
            connectionSocket.send(("HTTP/1.1 200 OK\r\nLast-Modified: " + nowTimeStr + " \r\n\r\n").encode())

            connectionSocket.send(filecontent.encode())

        # if nothing changed, i.e. return 304 header
        else:
            connectionSocket.send("\r\n\r\n".join(result).encode())
    # handle /update.html
    elif filename == "/update.html":
        connectionSocket.send("HTTP/1.1 200 OK\r\n\r\n".encode())

        # return the file contents
        filecontent = None
        with open("." + filename, "r") as f:
            filecontent = f.read().encode()

        connectionSocket.send(filecontent)
    # other file is invalid for security concern
    else:
        connectionSocket.send("HTTP/1.1 404 Not Found\r\n\r\n".encode())

    # Close the connection
    connectionSocket.close()

def main():
    # Listening port for the server
    serverPort = 8080

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
        # print(addr)
        # Create a new thread for a client
        t = threading.Thread(target=httpLink, args=(sock, addr))
        t.start()

if __name__ == '__main__':

    # Create a single instance of API
    api = API()

    # Create a write-lock
    writelock = threading.Lock()

    # Run main function
    main()
