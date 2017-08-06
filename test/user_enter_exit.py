import Pyro4, Pyro4.naming, sys, threading, time
sys.path.append('./src')
from message import NodeECState, MsgType, Message

sys.excepthook = Pyro4.util.excepthook
Pyro4.config.SERIALIZERS_ACCEPTED = set(['pickle'])
Pyro4.config.SERIALIZER = 'pickle'

nsinfo = sys.argv[1]
ns_name = nsinfo.split(":")[0]
ns_port = int(nsinfo.split(":")[1])
pyro_ns = Pyro4.locateNS(host=ns_name, port=ns_port)

# user enter sequence of events
def user_enter():
	Pyro4.Proxy(pyro_ns.lookup("Sensor.Door")).toggle_state("OPEN")
	Pyro4.Proxy(pyro_ns.lookup("Sensor.Door")).toggle_state("KEY")
	Pyro4.Proxy(pyro_ns.lookup("Sensor.Motion")).toggle_state("YES") 
	Pyro4.Proxy(pyro_ns.lookup("Sensor.Door")).toggle_state("CLOSED")
	Pyro4.Proxy(pyro_ns.lookup("Sensor.Motion")).toggle_state("NO")

# use exit sequence of events
def user_exit():
	Pyro4.Proxy(pyro_ns.lookup("Sensor.Motion")).toggle_state("YES")
	Pyro4.Proxy(pyro_ns.lookup("Sensor.Door")).toggle_state("OPEN")
	Pyro4.Proxy(pyro_ns.lookup("Sensor.Door")).toggle_state("CLOSED")
	Pyro4.Proxy(pyro_ns.lookup("Sensor.Motion")).toggle_state("NO")


start_time = time.time()
print("Starting simulation at {0}".format(start_time))
time.sleep(2)
user_enter()
end_time = time.time()
print("End simulation at {0}".format(end_time))
print("Durationi {0}".format(end_time - start_time))