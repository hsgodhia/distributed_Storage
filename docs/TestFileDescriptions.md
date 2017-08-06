## Test

All the test files are in the test directory

1. `cache_test.py` a test script prepared to test the key components of the cache, LRU eviction policy
2. `con_flt_repl.py` a test script prepared to test the scenarios of replication, sequential consistency and primary-backup remote write protocol fault tolerance
3. `raft_test.py` a test script to test the scenarios of key componenets of the RAFT protocol which is mainly the leadeer election and log replication
4. `user_enter_exit.py`
Run this program to simulate a user entry and exit. Key test: correct ordering of events and inference at the gateway to turn security system on/off, system mode to home/away

*Note*: 
 - Any of the test scripts of the lab 2 can be run since the functionality for theif enter, user enter exit, bulb on and off is the same. the test descriptions can be seen in the report of lab 2 since they stay the same  
 - To run any of the test file follow the command `python3 test_file.py <nameserver_ip:port>`

