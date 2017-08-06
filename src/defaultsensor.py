import Pyro4, Pyro4.naming, threading, time, sys, socket, random
from message import MsgType, Message, NodeECState
Pyro4.config.SERIALIZERS_ACCEPTED = set(['pickle'])
Pyro4.config.SERIALIZER = 'pickle'
sys.excepthook = Pyro4.util.excepthook

#the default base sensor implementation
@Pyro4.expose
@Pyro4.behavior(instance_mode="single")
class DefaultSensor():
	def __init__(self):
		self.gtyuri = None	#the variable which stores the gateway URI
		self.id = None		#the id of the sensor
		self.loopval = False	#the game loop control
		self.initGtyUri()

	#when received an RPC call with a gateway id, the sensor updates its gateway
	def updateGtyUri(self, gtyid):
		self.gtyuri = gtyid
		print("updated, {0} now assigned to {1}".format(self.id, self.gtyuri))
	
	#when the sensor starts up it runs this routine which ensures that the sensor is connected to gateway such load distribution is optimal 
	def initGtyUri(self):
		other_gtys = self.pyro_ns.list(metadata_all={"gateway"})		
		gty = random.choice(list(other_gtys.keys()))
		#choose a random gateway to connect to who inturn would connect the primary to fetch data
		self.gtyuri = Pyro4.Proxy(self.pyro_ns.lookup(gty)).getGtyuri()
		time.sleep(1)
		Pyro4.Proxy(self.pyro_ns.lookup("gateway:{0}".format(self.gtyuri))).connect_gty(self.stype + "." + self.name)
		print("initial gateway assignment to {0}".format(self.gtyuri))
		self.register()
		
	#method definition modified since only gateway has the ability to register other sensors/devices
	def register(self):
		self.id = Pyro4.Proxy(self.pyro_ns.lookup("gateway:{0}".format(self.gtyuri))).register(self.stype, self.name)
	
	#in a pull based sensor, gateway calls this method via RPC to get state info
	def query_state(self, id):
		return (self.id, self.state)

	def report_state(self, id, val):
		if id == self.id:
			self.state = val.data
		print("at ts {0} DELIVERED {1}".format(self.getNextRealts(), val))
		#no method implementation
		#a sensor doesn't keep track of states
		
	def change_state(self, id, state):
		pass
		#no method implementation
		#sensor doesn't have capability to change state of another device

	# -- util methods being --
	def push_data(self, msg):
		#push data via calling report_state on the gateway
		#before making a call to the gateway frontend check if the uri is still valid??
		num_tries = 10
		while num_tries > 0:
			#makes a maxium of 10 retries before declaring a failure
			val = Pyro4.Proxy(self.pyro_ns.lookup("gateway:{0}".format(self.gtyuri))).report_state(self.id, msg)
			if val:
				print("at ts {0} SEND event {1}".format(msg.ts, msg))
				break
			else:
				print("retrying!")
			num_tries -= 1
			time.sleep(1/2)
			#after every failure wait for 0.5 seconds 
		return val

	def toggle_state(self, msgdata):
		msg = Message(pid = self.id, data = msgdata, msg_type = MsgType.STATE, ts = self.getNextRealts() )
		if self.comtype == "push":
			self.push_data(msg)

