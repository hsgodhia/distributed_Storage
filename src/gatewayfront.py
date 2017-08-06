import Pyro4, Pyro4.naming, sys, random, threading, socket, time, traceback, queue, heapq
from message import MsgType, Message, NodeECState
from realprocess import RealProcess

_seq_lock = threading.Lock()
Pyro4.config.SERIALIZERS_ACCEPTED = set(['pickle'])
Pyro4.config.SERIALIZER = 'pickle'
sys.excepthook = Pyro4.util.excepthook
ELECTION_TIMEOUT = 1
CACHE_SIZE = 10

@Pyro4.expose
@Pyro4.behavior(instance_mode = "single")
class GatewayFront(RealProcess):
	def __init__(self, pid):
		global ns_name, ns_port
		self.pyro_ns = Pyro4.naming.locateNS(host=ns_name, broadcast=False, port=ns_port)
		self.id = pid

		#simple store to avoid making new connections every time
		self.proxies = {}
		self.prevlogline = ""
		self.state = NodeECState.PARTICIPANT
		#an incrementing sequence to assign ids to devices and processes
		self._seq = pid + 1

		#a dictionary mapping the id of a gateway to a list of client URIs it holds
		self.con_clients = {}
		self.cache = [] # a max-heap of records maintained in-memory for caching
		#server processes which are down at any point in time
		self.down = {}
		#servers which are done balancing
		self.done_balancing = []
		self.con_clients[self.id] = []

		#this is a data structure which needs to be synced/consistency here
		self._processids = {}

		#blocking queue to receive messages if this replica is a primary
		self.central_qu = queue.Queue()
		#create an instance of the backend, it will be a shared proxy
		self._dbproxy = Pyro4.Proxy(self.pyro_ns.lookup("db:{0}".format(pid)))
		RealProcess.__init__(self)

		#starting the background hearbeat thread
		t = threading.Thread(target = self.heartbeat)
		t.setDaemon(True)
		t.start()

		#starting the background leader election thread
		t = threading.Thread(target = self.leaderelection)
		t.setDaemon(True)
		t.start()

		#starting the primary queue reader thread
		t2 = threading.Thread(target = self.primary_qu_reader)
		t2.setDaemon(True)
		t2.start()

	#raft: leader election
	def leaderelection(self):
		while 1:
			time.sleep(ELECTION_TIMEOUT)
			maxid = 0
			for k in self.con_clients:
				if k not in self.down:
					maxid = max(maxid, k)

			#print("running election on: {0} winner : {1}".format(self.con_clients, maxid))
			if self.id == maxid:
				if self.state != NodeECState.LEADER:
					print("i'm becoming the leader-primary replica")	
				self.state = NodeECState.LEADER
			else:
				if self.state != NodeECState.PARTICIPANT:
					print("i'm becoming the a slave replica")	
				self.state = NodeECState.PARTICIPANT

	def getnodestate(self):
		return self.state

	# a method which enables other process to register with the gateway and get a PID
	def register(self, ptype, pname):
		pid = self.getNextPid()
		self._processids[pid] = (ptype, pname)
		self._dbproxy.register(pid, pname)
		return pid

	def query_state(self, pid):
		#get current state from db and report
		return self._dbproxy.query_state(pid)			

	# a name to pid translation service
	def nametopid(self, name):
		for k in self._processids:
			if self._processids[k][1] == name:
				return k

	def add_record(self, pid, val):
		if pid not in self._processids:
			print("{0} not found in local list front".format(pid))
			return
		cpname = self._processids[pid][1]
		if cpname == "Motion" and val.msg_type == MsgType.STATE and val.data == "YES":
			bulb = self.nametopid("Bulb")
			print("Gateway Remotely switiching ON bulb")
			#sending a remote message to remotely turno ON the bulb
			self.change_state(bulb, "ON")
		elif cpname == "Motion" and val.msg_type == MsgType.STATE and val.data == "NO":
			bulb = self.nametopid("Bulb")
			print("Gateway Remotely switiching OFF bulb")
			#sending a remote message to remotely turno OFF the bulb
			self.change_state(bulb, "OFF")

		self._dbproxy.report_state(pid, val)
		return True

	#key is the clock value at which you want to know system state
	def get_from_cache(self, key):
		for rec in self.cache:
			val = rec[1]
			if val.split(" ")[-1] == 'clock:{0}'.format(key):
				return val
		return None

	#if required to fetch from file call backend gateway to return file
	def get_from_file(self, key):
		return self._dbproxy.get_from_file(key)

	#pass the key:clock value to get state of the system at that time
	def get_record(self, key):
		val = self.get_from_cache(key)
		if val is not None:
			#update access time of the element, if it is accessed from the cache
			for ind in range(len(self.cache)):
				if self.cache[ind][1] == val:
					rind = ind
					break

			del self.cache[rind]
			heapq.heappush(self.cache, (self.getNextRealts(), val))
			print('found {0} in cache'.format(key))
		else:
			#if element not found in cache then fetch from file
			val = self.get_from_file(key)
			if val is None:
				print("did not find {0} in file".format(key))
				return  None

			if len(self.cache) >= CACHE_SIZE:
				evict = heapq.heappop(self.cache)
				print("evicted record {0}".format(evict))
				#if size is overflow, pop least recently used and push current element
			heapq.heappush(self.cache, (self.getNextRealts(), val))
			#each element is pushed with its clock value representing its access time
			print('geting from file/db')
			
		print('cache size: ', len(self.cache))
		print('cache contents: ', self.cache)
		return val
	
	#all events send to the primary are queued to ensure orderly dilvery
	def add_to_qu(self, pid, val):
		tup = (pid, val)
		self.central_qu.put(tup)
		return True

	#the daemon thread which reads the queue
	def primary_qu_reader(self):
		while 1:
			tup = self.central_qu.get()
			val = self.ldr_report_state(tup[0], tup[1])
			if val == False:
				print("message {0} delivery failed!".format(tup))

	def ldr_report_state(self, pid, val):
		#add to a common single blocking queue and read from there
		gtys = self.pyro_ns.list(metadata_all={"gateway"})		
		for k in gtys:
			uri = gtys[k]
			pid = int(k.split(":")[1])
			try:
				st = Pyro4.Proxy(uri).add_record(val.frompid, val)
				if st is False:
					return False
			except Exception:
				print("leader failed to forward to backup {0}".format(k))
		return True

	def report_state(self, pid, val):
		msg_ts = self.getNextRealts()
		val.ts = msg_ts
		#FORWARD the write request to the primary
		gtys = self.pyro_ns.list(metadata_all={"gateway"})		
		ldrs = []
		for k in gtys:			
			uri = gtys[k]
			pid = int(k.split(":")[1])
			if k in self.down:
				continue
				#no need to check if a down machine is a leader, it has to be a live node
			try:
				st = Pyro4.Proxy(uri).getnodestate()
				if st == NodeECState.LEADER:
					ldrs.append(uri)
			except Exception:
				#print(traceback.format_exc())
				print("{0} is down3!".format(pid))

		if len(ldrs) == 1:
			#only one leader can prooceed to forward request to it
			try:
				print("ts: {0} DELIVERED {1}".format(msg_ts, val))
				return Pyro4.Proxy(ldrs[0]).add_to_qu(pid, val)
			except Exception:
				return False
		else:
			print("incorret {0} number of leaders..aborting".format(ldrs))
			return False

	#the frontend gateway has ability to toggle the state of another device/sensor and control it remotely
	def change_state(self, pid, new_state):
		if pid in self._processids:
			Pyro4.Proxy(self.pyro_ns.lookup(self._processids[pid][0] + "." + self._processids[pid][1])).toggle_state(new_state)
			if pid != self.id:
				nmsg = Message(new_state, MsgType.STATE, pid)
				#self._dbproxy.report_state(pid, nmsg)

	# atomic operation to icnrement prcess PID which is assigned to different proceses
	def getNextPid(self):
		global _seq_lock
		with _seq_lock:
			self._seq += 1
			pid = self._seq
		return pid

	#an RPC call made to a gateway replica to take on the new load passed as param and serve it
	def serve_client(self, uri_name):
		print("{1} got new load {0}".format(uri_name, self.id))
		self.newload(self.id, uri_name)
		Pyro4.Proxy(self.pyro_ns.lookup(uri_name)).updateGtyUri(self.id)
		return True

	#update the record that gatewaruy:pid now also servers uri_name  
	def newload(self, pid, uri_name):
		if pid not in self.con_clients:
			self.con_clients[pid] = []
		self.con_clients[pid].append(uri_name)

	#get the lates full load of gateway:pid
	def saveLoad(self, pid, load):
		#print("current loads", self.con_clients)
		self.con_clients[pid] = load

	#raft: method implementation for log replication
	def logrepl(self, otherproid):
		if str(otherproid) == self.prevlogline:
			return
			#no need to write to the log if the data is the same as seen previously
		else:
			self.prevlogline = str(otherproid)

		with open("log_{0}.txt".format(self.id), 'a') as fp:
			if len(otherproid) >= 1:
				fp.write(str(otherproid))
				fp.write("\n")

		for k in otherproid:
			if k not in self._processids:
				self._processids[k] = otherproid[k]
				print("local list update {0}".format(self._processids))
				self._dbproxy.register(k, self._processids[k][1])

	#find the least loaded gateway based upon the localsnapshot held by self.con_clients and return the pid
	def getLeastLoadedGty(self, ex_pid = None):
		min_l, min_pid = 99999999, None
		print(self.con_clients)
		for k in self.con_clients:
			if ex_pid is not None:
				if k == ex_pid:
					continue
			cur = len(self.con_clients[k])
			if cur < min_l:
				min_l = cur
				min_pid = k

		return min_pid

	#find an overloaded gateway to shift load off and return its pid
	def getOverloadedGty(self):
		if len(self.con_clients) < 1:
			return None
		t = 0
		for k in self.con_clients:
			t += len(self.con_clients[k])
		avg = t//len(self.con_clients)
		for k in self.con_clients:
			if k > avg:
				return k

	#when a gateway replica recovers from a crash this method is ran
	def rebalance(self, pid, clts):
		self.done_balancing.remove(pid)
		opid = self.getOverloadedGty()
		if opid is None:
			return True

		#shift over half of the load of the most overloaded machine
		half = len(self.con_clients[opid])//2
		if half < 1:
			return True

		suc = True
		for i in range(half):
			c = self.con_clients[opid][i]
			#for each load find the least loaded machine to assign to
			upid = self.getLeastLoadedGty()
			if upid is None:
				return True
			try:
				suc = suc and Pyro4.Proxy(self.pyro_ns.lookup("gateway:{0}".format(upid))).serve_client(c)
			except Exception:
				print(traceback.format_exc())
				suc = False

		if suc == True:
			self.con_clients[opid] = self.con_clients[opid][half:]
		return suc

	#balance the load originally served by gateway:pid due to its crash
	def balance(self, pid, clts):
		if pid in self.done_balancing:
			return
		
		if clts is not None and len(clts) > 0:
			print("balancing {0} after failure of {1}".format(clts, pid))
			for c in clts:
				n_pid = self.getLeastLoadedGty(pid)
				try:
					suc = Pyro4.Proxy(self.pyro_ns.lookup("gateway:{0}".format(n_pid))).serve_client(c)
				except Exception:
					suc = False
					#print(traceback.format_exc())
					print("connection to {0} failed".format(n_pid))
		else:
			suc = True
		if suc == True:
			self.done_balancing.append(pid)

	#execute heartbeet every 1/10 of a sec, propogate the latest load values 
	def heartbeat(self):
		cnt = 0
		while 1:
			time.sleep(1/10)
			other_gtys = self.pyro_ns.list(metadata_all={"gateway"})		
			#fetch all other gateway replicas from the system
			for k in other_gtys:
				if k == "gateway:{0}".format(self.id):
					continue

				uri = other_gtys[k]
				pid = int(k.split(":")[1])
				#print('down', self.down)
				try:
					if uri not in self.proxies:
						self.proxies[uri] = Pyro4.Proxy(uri)
					#heart beat exchanges new load and log replication information with each of the clients
					self.proxies[uri].saveLoad(self.id, self.con_clients[self.id])
					self.proxies[uri].logrepl(self._processids)
					if pid in self.down:
						clts = self.down.get(pid, None)

						if self.state == NodeECState.LEADER:
							suc = self.rebalance(pid, clts)
							print("{0} cameback up, rebalance {1} was {2}!".format(pid, clts, suc))
							if suc == True:
								self.down.pop(pid, None)
						else:
							self.down.pop(pid, None)
				except Exception:
					#print(traceback.format_exc())
					if pid not in self.down:
						clts = self.con_clients.get(pid, None)
						self.down[pid] = clts
						print("{0} is down1!".format(k))
						
					if self.state == NodeECState.LEADER:
						self.balance(pid, self.down[pid])
						if pid in self.done_balancing:
							self.con_clients.pop(pid, None)
					else:
						self.con_clients.pop(pid, None)

					cnt += 60

			cnt += 1
			if cnt >= 600:
				#print the distribution of the load every minute
				print("current distr: ", self.con_clients, flush=True)
				cnt = 0
	
	def connect_gty(self, uri_name):
		self.newload(self.id, uri_name)		

	#multicast it to all the gateways
	def getGtyuri(self):
		gtys = self.pyro_ns.list(metadata_all={"gateway"})
		for k in gtys:
			uri = gtys[k]
			try:
				gty = Pyro4.Proxy(uri).getGtyuri_internal()
				if gty is not None:
					return gty
			except Exception:
				print("{0} is down!".format(uri))

	def getGtyuri_internal(self):
		if self.state == NodeECState.LEADER:
			gtyid = self.getLeastLoadedGty()
			return gtyid
		else:
			return None

if __name__ == '__main__':
	global ns_name, ns_port
	nsinfo = sys.argv[1]
	ns_name = nsinfo.split(":")[0]
	ns_port = int(nsinfo.split(":")[1])
	pid = int(sys.argv[2])
	print("gateway running with below uri: ",flush=True)
	gtfront = GatewayFront(pid)

	with Pyro4.core.Daemon(host=socket.gethostbyname(socket.gethostname())) as daemon:
		with Pyro4.naming.locateNS(host=ns_name, broadcast=False, port=ns_port) as ns:
			uri = daemon.register(gtfront, "gateway:{0}".format(pid))
			print(uri, flush=True)
			#print "URI is : ", uri
			ns.register("gateway:{0}".format(pid), uri, metadata={"gateway"})
		daemon.requestLoop()