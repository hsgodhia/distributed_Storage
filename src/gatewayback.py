import threading, Pyro4, Pyro4.naming, sys, time, collections, socket
from realprocess import RealProcess

sys.excepthook = Pyro4.util.excepthook
Pyro4.config.SERIALIZERS_ACCEPTED = set(['pickle'])
Pyro4.config.SERIALIZER = 'pickle'

@Pyro4.expose
@Pyro4.behavior(instance_mode = "single")
class GatewayBack(RealProcess):
	def __init__(self, pid):
		global ns_name, ns_port
		self.pyro_ns = Pyro4.naming.locateNS(host=ns_name, broadcast=False, port=ns_port)
		RealProcess.__init__(self)
		
		self.id = pid
		self.iskey = False
		#ordered dict so that every time we print to file in same order
		self.states = collections.OrderedDict()
		#initial states of the devices/sensor is set to NA
		self.states["Motion"] = "NA"
		self.states["Door"] = "NA"
		self.states["Temperature"] = "NA"
		self.states["Bulb"] = "NA"
		self.states["Outlet"] = "NA"
		#the file handle to our backend storage
		self.filehandle = open("db_{0}.txt".format(self.id), "a")
		self.leader = None
		self.proids = {}
		self.fsm = 0
		self.add_record(0)

	def change_state(self, pid, new_state):
		pass

	def getstate(self):
		return self.states

	def updatestate(self, otherstate):
		for k in otherstate:
			self.states[k] = otherstate[k]

	def register(self, pid, pname):
		self.proids[pid] = pname

	def query_state(self, pid):
		return self.states[pid]

	def report_state(self, pid, val):
		if pid not in self.proids:
			print("pid {0} not found in local list back".format(pid))
			return
		# a finite state machine which has no storage except for one variable 'fsm'
		if self.proids[pid] == "Door" and val.data == "KEY":
			self.iskey = True
		elif self.fsm == 0 and self.proids[pid] == "Door" and val.data == "OPEN":
			self.fsm = 1
		elif self.fsm == 1 and self.proids[pid] == "Motion" and val.data == "YES":
			self.fsm = 2
		elif self.fsm == 2 and self.proids[pid] == "Door" and val.data == "CLOSED":
			self.fsm = 3
		elif self.fsm == 3 and self.proids[pid] == "Motion" and val.data == "NO":
			self.fsm = 4
		else:
			self.fsm = 0

		self.states[self.proids[pid]] = val.data

		#for each state change a record is added to the database
		self.add_record(val.ts)
		if self.fsm == 4:
			self.fsm = 0
			if self.iskey:
				self.add_msg("MSG: User Enters House, MODE: HOME, SECURTIY: DISABLED \n")
				self.iskey = False
			else:
				self.add_msg("MSG: Theif Enters House, ALARM RING !! \n")

	def add_msg(self, msg):
		self.filehandle.write(msg)
		self.filehandle.flush()

	#key is the clock value at which time you want to know system state
	def get_from_file(self, key):
		#automatically opens and closes file
		with open("db_{0}.txt".format(self.id), 'r') as fp:
			for val in fp:
				val = val.strip()
				if val.split(" ")[-1] == 'clock:{0}'.format(key):
					return val

	def add_record(self, ts):
		val = ""
		for k in self.states:
			val += "{0}:{1} ".format(k, self.states[k])
		line = val + " clock:" + str(ts) + "\n"
		self.filehandle.write(line)
		self.filehandle.flush()

	def get_leader(self):
		return self.leader

	def set_leader(self,name):
		self.leader = name

if __name__ == '__main__':
	global ns_name, ns_port
	nsinfo = sys.argv[1]
	ns_name = nsinfo.split(":")[0]
	ns_port = int(nsinfo.split(":")[1])
	pid = int(sys.argv[2])

	print("db running with below uri: ")
	gtback = GatewayBack(pid)
	
	with Pyro4.core.Daemon(host=socket.gethostbyname(socket.gethostname())) as daemon:
		with Pyro4.naming.locateNS(host=ns_name, broadcast=False, port=ns_port) as ns:
			uri = daemon.register(gtback, "db:{0}".format(pid))
			print(uri)
			ns.register("db:{0}".format(pid), uri, metadata={"db"})
		daemon.requestLoop()