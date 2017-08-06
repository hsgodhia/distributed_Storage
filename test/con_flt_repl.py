import Pyro4, Pyro4.naming, sys, random, threading, socket
sys.excepthook = Pyro4.util.excepthook
Pyro4.config.SERIALIZERS_ACCEPTED = set(['pickle'])
Pyro4.config.SERIALIZER = 'pickle'

nsinfo = sys.argv[1]
ns_name = nsinfo.split(":")[0]
ns_port = int(nsinfo.split(":")[1])

pyro_ns = Pyro4.naming.locateNS(host=ns_name, broadcast=False, port=ns_port)
lt = pyro_ns.list(return_metadata=True)

def event(val):
	for k in lt:
		if "gateway" in k:
			continue
		if "db" in k:
			continue
		if "NameServer" in k:
			continue
		
		Pyro4.Proxy(lt[k][0]).changeloopval(val)

event("end") #will make every sensor/device print a message every 10s
			
