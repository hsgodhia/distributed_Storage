import Pyro4, Pyro4.naming, threading, time, sys

sys.excepthook = Pyro4.util.excepthook
Pyro4.config.SERIALIZERS_ACCEPTED = set(['pickle'])
Pyro4.config.SERIALIZER = 'pickle'

_realclock_lock = threading.Lock()

@Pyro4.expose
class RealProcess():
	def __init__(self):
		self.clock = 0

	#setter method for the real clock
	def setRealts(self, new_clock):
		global _realclock_lock
		with _realclock_lock:
			self.clock = new_clock

	#getter method for the real clock
	def getRealts(self):		
		return self.clock

	#atomic operation for increment of real clock value (currently it increments it by the self.id value)
	def getNextRealts(self):
		global _realclock_lock
		with _realclock_lock:
			#the clock tick rate is different for each process (currently set the tick rate at 2*id of clock)
			self.clock += 1
			ts = self.clock
		return ts