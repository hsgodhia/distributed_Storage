## Source files

All the files are in the src directory

1. `x_sensor.py` names are given to all sensors
2. `x_device.py` names are given to all devices
3. `defaultsensor.py` and `defaultdevice.py` are base classes which each sensor and device inherits from
4. `gatewayfront.py` is the name assigned to the frontend gateway
5. `gatewayback.py` is the name assigned to the backend gateway
6. `message.py` contains the common message wrapper which we use as the payload when passing messages using RPC. The enums we use to maintain are in this file as well.
```python
class NodeECState(Enum):
    PARTICIPANT = 1
    NON_PARTICIPANT = 2	
    LEADER = 3		#node state for a process who is the leader
    
class MsgType(Enum):
    ACK = 1			#used for totally ordered multicast
    DATA = 2		#used for general data
    STATE = 3		#used to indicate state change info
    ELECTION = 4	#used for ring election algorithm
    LEADER = 5 		#used for ring election algorithm
```

7. Basic clock primitives are present in `realprocess.py`
8. `db_<PID>.txt` which contains persistent storage and where all state change evnets are logged by the backend gateway, the file name contains the PID of the replica to which the file corresponds to. It also contains important messages and alerts like user enters house, alarm ring etc. When runned remotely on different machines this file will be located on each of the node of the backend gateway
9. `read_db.py` present in the `test` directory is a util file to process the logs generated in the `db_<PID>.txt`
10.`log_<PID>.txt` which contains the log records as per the log replication of the RAFT protocol