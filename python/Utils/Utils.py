import json
import requests
iUtils = None

#Takes message OBJECT , not string
def handleMessage(msg, conn):
    mtype = msg.getType()
    if mtype == "help":
        #new logic
        print("new help request")
        if (iUtils.getQueue().get(msg.getUID()) != None ):
            conn.sendMessage("""
            { 
            "type": "response",
            "body" : "You shouldn't spam the server.  Please cancel and re-try the request" 
            }
            """.encode(encoding='UTF-8'))
        else:
            #create user object
            u = User(conn, msg.getUID(), msg.getEmail())
            #add user to active users lists
            iUtils.activeUsers[conn] = [u, "users"]
            #Add the user to the group list
            iUtils.getGroup('users').addMember(u)
            #Forward the message to the Mentors group
            #for mentors, this is called an add request
            msg.setType('add')
            iUtils.getGroup("mentors").sendAll(msg)

            iUtils.queueRequest(msg)

            #let the user know we arent taking requests right now
            conn.sendMessage("""
                { 
                "type": "response",
                "body" : "Your request has been queued" 
                }
            """.encode(encoding='UTF-8'))


    elif mtype == "newmentor":
        #newmentor logic
        print("mentor regitration")
        #create group object
        u = User(conn, msg.getUID(), msg.getEmail())
        iUtils.activeUsers[conn] = [u, "mentors"]
        iUtils.getGroup("mentors").addMember(u)

        print("mentor list now consists of...")
        for m in iUtils.getGroup("mentors").getAll():
            print(m.getUID())

        #send the mentor the list of queued requests.
        for k,v in (iUtils.getQueue().items()):
            u.send(v)

    elif mtype == "helpack":

        print("helpack")
        mentorUID = msg.getUID();
        #the mentor clicked respond, and is drafting a response.
        targetQueuedItemUID = msg.getContent()['targetUID']
        targetQueuedItem = iUtils.getQueue()[targetQueuedItemUID]

        user = iUtils.getGroup('mentors').getMember(mentorUID);
        # See if the request is blocked
        if not targetQueuedItem.isBlocked():
            print("grant the lock") 
            response = iUtils.lockResponse(targetQueuedItemUID, 'granted') 
            user.send(response)
            targetQueuedItem.blocked = True
            iUtils.locks[msg.getUID()] = targetQueuedItem

            #Tell everyone else the lock has been granted.
            iUtils.sendOthers(mentorUID, iUtils.lockResponse(targetQueuedItemUID, 'denied'))
        else:
            #blocked.  Say NO
            response = iUtils.lockResponse(targetQueuedItemUID, 'denied')
            user.send(response)
            print("cant have it")
        print("help acknowleged")

    elif mtype == "cancel": #a mentor retracts their block
        #the mentor dediced not to send their message
        if (msg.getContentValue('uid') != None):  
            targetQueuedItemUID = msg.getContent()['uid']
            targetQueuedItem = iUtils.getQueue()[targetQueuedItemUID]
            targetQueuedItem.blocked = False
            del iUtils.locks[msg.getUID()]
            iUtils.groups['mentors'].sendAll(iUtils.lockResponse(targetQueuedItemUID, 'released'))
            print("Mentor " + msg.getUID() + " Cancelled their block");

    elif mtype == "respond": 
        print(msg.getContent())
        mentorUID = msg.getUID()
        targetQueuedItemUID = msg.getContent()['targetUID'];
        targetQueuedItem = iUtils.getQueue()[targetQueuedItemUID]

        user = iUtils.getGroup("users").getMember(targetQueuedItemUID);
        #Dont need to check blocking.  If they send a helpResponse, they already asked for the lock

        #respond to the client here
        #msg.type = "response"; 
        #Try because they may have quit
        try:
            user.send(msg)
        except:
            pass

        #email the user before we delete their message.
        userEmail = targetQueuedItem.getEmail()
        mentorName = msg.getContentValue('name')
        mentorEmail = msg.getContentValue('email')
        #send to mentor.
        userMessage =  {
        "from" : mentorName + "<" + mentorEmail + ">",
        "to" : [userEmail],
        "subject" : "You Have A Mentor Response!",
        "text" : msg.getRaw()
        }

        iUtils.sendEmail(userMessage)

        try:
            del iUtils.requests[targetQueuedItemUID]
        except:
            pass
        iUtils.getGroup('mentors').sendAll(iUtils.removeRequest(targetQueuedItemUID))

    elif mtype == "remove": # what happens when a client cancels their own request
        try:
            del iUtils.requests[msg.getUID()]
        except:
            pass
        iUtils.getGroup('mentors').sendAll(iUtils.removeRequest(msg.getUID()))


def handleClose(conn):
    # import pdb; 
    # pdb.set_trace()
    user = iUtils.activeUsers.pop(conn) # typle (user obj, group name string)

    iUtils.getGroup(user[1]).removeMember(user[0])
    if (iUtils.locks.get(user[0].getUID()) != None):
        iUtils.locks.get(user[0].getUID()).blocked = False
        del iUtils.locks[user[0].getUID()]



class utils:

    def __init__(self, groupDict):
        self.groups = groupDict
        self.requests = {}
        self.activeUsers = {}
        self.locks = {}

    def getGroup(self, groupName):
        return self.groups[groupName]

    def getAllGroups(self):
        return self.groups

    def queueRequest(self, message):
        self.requests[message.getUID()] = message

    def getQueue(self):
        return self.requests

    def newHelpResponse(self, targetUID, body, senderUID):
        print(body)

    def getActiveUsers(self):
        return self.activeUsers

    def lockResponse(self, targetUID, lockStatus):
        lock = {'type' : 'lock', 'uid' : targetUID, 'status': lockStatus}
        msg = Message(json.dumps(lock))
        return msg

    def removeRequest(self, UID):
        remove = {'type' : 'remove', 'uid': UID }
        msg = Message(json.dumps(remove))
        return msg

    def sendOthers(self, UIDnotToSend, message):
        for m in self.groups['mentors'].getAll():
            if m.getUID() != UIDnotToSend:
                m.send(message)

    def sendEmail(self, msgJson):
        eurl = "https://api.mailgun.net/v2/sandboxc8545debcab1457da56af08ddc945353.mailgun.org/messages"
        authy = ("api", "key-d5adf31fdfa64913b16bd55261f6e24a")

        return requests.post(eurl, auth=authy, data=msgJson)



    #map connections to user objects

class Group:

    def __init__(self, name):
        self.name = name
        self.members = {}

    def addMember(self, member):
        self.members[member.getUID()] = member

    def sendAll(self, message):
        for k,v in self.members.items():
            v.send(message)

    def removeMember(self, member):
        try:
            del self.members[member.getUID()]
        except:
            print("cant remove member")

    def getAll(self):
        return self.members.values()

    def getMember(self, uid):
        return self.members.get(uid)


class User:

    def __init__(self, ws, uid, email):
        self.ws = ws
        self.uid = uid
        self.email = email
        self.locks = []

    def send(self, message):
        self.ws.sendMessage(message.getRaw().encode(encoding='UTF-8'))

    def getUID(self):
        return self.uid

    def getWS(self):
        return self.ws

    def getEmail(self):
        return self.email

    def releaseLocks(self):
        for l in self.locks:
            l.setBlocked(False)
            #notify others that the lock was released
            iUtils.getGroup("mentors").sendAll(iUtils.lockResponse(l.getUID(), 'released'))

class DebugUser:

    def send(self, message):
        print("Debug user says %s" % message)

    def getUID(self):
        return("Debug User")

class Message:

    def __init__(self, message):
        self.msg = message
        self.json = json.loads(self.msg)
        self.blocked = False

    def getType(self):
        return self.json['type']

    def setType(self, mtype):
        self.json['type'] = mtype;

    def getContent(self):
        return self.json.get('body')

    def getUID(self):
        return self.json['uid']

    def getEmail(self):
        return self.json.get('email', 'no emaill provided')

    def getRaw(self):
        return json.dumps(self.json)

    def isBlocked(self):
        return self.blocked

    def setBlocked(self, b):
        self.blocked = b;

    def getContentValue(self, key):
        if (self.json.get('body') != None):
            if(self.json.get('body').get(key) != None):
                return self.json.get('body').get(key)
        else:
            return None;

    def getValue(self, key):
        if(self.json.get(key) != None):
            return self.json.get(key, "not found")
