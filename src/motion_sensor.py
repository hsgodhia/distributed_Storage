import Pyro4, Pyro4.naming, threading, time, sys, random, queue, socket
from message import MsgType, Message

from defaultsensor import DefaultSensor
from realprocess import RealProcess
#every device and sensor inherit from the default device and sensor respectively 
sys.excepthook = Pyro4.util.excepthook

@Pyro4.expose
@Pyro4.behavior(instance_mode="single")
class Motion_sensor(DefaultSensor, RealProcess):
	def __init__(self, stype, name, comtype):
		global ns_name, ns_port
		self.pyro_ns = Pyro4.naming.locateNS(host=ns_name, broadcast=False, port=ns_port)
		self.stype = stype
		self.comtype = comtype
		self.name = name

		RealProcess.__init__(self)
		DefaultSensor.__init__(self)

		#each sensor is made to run a continuous loop to stream events as a simulation
		t = threading.Thread(target = self.gameloop)
		t.setDaemon(True)
		t.start()

	#main continous event streaming loop
	def gameloop(self):
		i = 1000
		while 1:
			time.sleep(20)
			if self.loopval is False:
				continue

			#(self, data, msg_type, pid, id=None, ts=None):
			i += 1
			msg = Message(i, MsgType.STATE, self.id)
			try:
				val = self.push_data(msg)
				if val is False:
					print("message {0} delivery failed!".format(i))	
			except Exception:
				print("message {0} delivery failed!".format(i))

	#to toggle the loop on and off 
	def changeloopval(self, val):
		if val == "start":
			self.loopval = True
		elif val == "end":
			self.loopval = False

if __name__=="__main__":
	global ns_name, ns_port
	nsinfo = sys.argv[1]
	ns_name = nsinfo.split(":")[0]
	ns_port = int(nsinfo.split(":")[1])

	obj = Motion_sensor("Sensor", "Motion", "push")
	print("Device: {0} assigned id: {1} running with below uri.".format(obj.name, obj.id), flush=True)

	with Pyro4.core.Daemon(host=socket.gethostbyname(socket.gethostname())) as daemon:
		with Pyro4.naming.locateNS(host=ns_name, broadcast=False, port=ns_port) as ns:
			uri = daemon.register(obj, obj.stype + "." + obj.name)
			print(uri, flush=True)
			ns.register(obj.stype + "." + obj.name, uri)
		#make a new thread, daemon-true
		daemon.requestLoop()