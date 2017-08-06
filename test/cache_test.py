import Pyro4, Pyro4.naming, sys, random, threading, socket, time

sys.excepthook = Pyro4.util.excepthook
Pyro4.config.SERIALIZERS_ACCEPTED = set(['pickle'])
Pyro4.config.SERIALIZER = 'pickle'

nsinfo = sys.argv[1]
ns_name = nsinfo.split(":")[0]
ns_port = int(nsinfo.split(":")[1])

pyro_ns = Pyro4.naming.locateNS(host=ns_name, broadcast=False, port=ns_port)
gtyid = 1000
print('getting event at time {0}'.format(sys.argv[2]))
start = time.perf_counter()
val = Pyro4.Proxy(pyro_ns.lookup("gateway:{0}".format(gtyid))).get_record(int(sys.argv[2]))
end = time.perf_counter()
elapsed = end - start
print("elapsed time = {:.12f} seconds".format(elapsed))
print('value is = ',val)