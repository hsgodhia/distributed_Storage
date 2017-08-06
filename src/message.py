from enum import Enum

class NodeECState(Enum):
    PARTICIPANT = 1
    NON_PARTICIPANT = 2
    LEADER = 3
    
class MsgType(Enum):
    ACK = 1
    HEARTBEET = 2
    STATE = 3
    ELECTION = 4
    LEADER = 5
    LOAD = 6

class Message(object):
    def __init__(self, data, msg_type, pid, id=None, ts=None):
        self.data = data
        self.msg_type = msg_type
        self.frompid = pid
        self.msgid = id
        self.ts = ts
        
    def __lt__(self, msg):
        if self.ts< msg.ts:
            return True
        elif self.ts > msg.ts:
            return False
        else:
            return self.frompid < msg.frompid
        
    def __repr__(self):
        return "(id:{0}, {1}, data: {2}, ts: {3}, from: {4})".format(self.msgid, self.msg_type, self.data, self.ts, self.frompid)

    def __str__(self):
        return "(id:{0}, {1}, data: {2}, ts: {3}, from: {4})".format(self.msgid, self.msg_type, self.data, self.ts, self.frompid)