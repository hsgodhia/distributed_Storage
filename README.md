# spring17-lab3

## How to run

1. Open a terminal where we would run the name server. Since we use custom classes for message passing, the serializer needs to be mentioned to the name server. This can be done by issuing the command  `export PYRO_SERIALIZERS_ACCEPTED=serpent,json,marshal,pickle`

2. Now we can start the python nameserver `python3 -m Pyro4.naming --host=<Host_IPaddr>`

3. Start the `gatewayback.py` backend db process. Note assign a unique <PID> to the process as a command line argument
ex: `python3 ./src/gatewayfront.py localhost:9090 1000` where the PID is 1000

4. Similarly, start the `gatewayfront.py` frontend process. Note, the PID assigned to the frontend should be the same as that assigned to the backend, since they work in paris

5. Now we start multiple such replicas. *Note*: please assign each replica a PID which is spaced out by atleast 1000, this is just done to ensure easy testing

5. Start the various sensors and devices (their PIDs are automatically assigned)

6. Run the various test from the test folder

*Note:*
 - Please start the proceses in the above order as frontend talks to backend and other devices talk to the frontend gateway
 - To start any of the devices `x_device.py` or sensor `x_sensor.py` or frontend and backend gateway we run the command
   `python3 x_device.py ns_name:ns_port` 
    where ns_name and ns_port correspond to the name server host name and port number
 - Similarly, to run any test script from the tes directory issue the command `python3 <test_file>.py ns_name:ns_port`
 - This has been tested on Pyro4 and python3

## Files

- The [lab report](report.docx) contains bulk of the design and architecture of the system as well as detailed test cases and their analysis
- A description of all the source files and code is given [here](docs/SourceFileDescriptions.md)
- A description of all the test files and code is give [here](docs/TestFileDescriptions.md)

### Team (individual)
- Harshal Godhia (hgodhia@cs.umass.edu)