Door_O = "Door:OPEN"
Door_C = "Door:CLOSED"
MOTION = "Motion:YES"
NO_MOTION = "Motion:NO"
HAS_KEY = "Door:KEY"

# since cahnges are consecutive, use a tuple to represent a event which occurs when all element is true
owner_returning = (False,False,False) #motion:no, door:open, door:key
owner_leaving = (False,False,False) #motion:yes, door:open, door:key

def is_event(e):
    rs = e[0]
    for i in e:
        rs = rs and i
    return rs
#reset event tuple to False everywhere
def reset_event(e):
    for i in e :
        i = False

def set_event(e,index):
    e[index] = True

db = open("../db_1000.txt", "r")
for line in db.readlines():
    if MOTION in line:
        set_event(owner_leaving,0)
    if NO_MOTION in line:
        set_event(owner_returning,0)
    if Door_O in line:
        set_event(owner_leaving,1)
        set_event(owner_returning,1)
    if HAS_KEY in line:
        set_event(owner_leaving,2)
        set_event(owner_returning,2)

    if is_event(owner_leaving):
        print("Owner leaves")
        reset_event(owner_leaving)

    if is_event(owner_returning):
        print("Owner returns")
        reset_event(owner_returning)