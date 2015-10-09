from autobahn.twisted.websocket import WebSocketServerProtocol
from Utils import Utils
import json

#accepts a message object, not a string


class MentorProtocol(WebSocketServerProtocol):

    def onMessage(self, payload, isBinary):
        ## echo back message verbatim
        # print(payload.decode('utf8'))
        # Option for message headers:
        # newmentor
        # setmentorprefs
        # help
        # helpack
        # helpexpire
        # helpreply
        m = ""
        try:
            #create a message object for the sender
            m = Utils.Message(payload.decode('utf8'))
        except :
            print("received bad message")
            self.sendClose()

        #handle will decide what needs to be done!
        Utils.handleMessage(m, self)


    def onConnect(self, request):
        # Connection logic
        print("Connection Established")

    def onClose(self, wasClean, code, reason):
        print("connection closed")
        Utils.handleClose(self);

    def onOpen(self):
        print("connection opened")

