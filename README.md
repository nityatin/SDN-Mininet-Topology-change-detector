# SDN-Mininet-Topology-change-detector
Detects changes in network topology dynamically.

**Course:** UE24CS252B — Computer Networks  
**Controller:** Ryu 
**Emulator:** Mininet 
**Protocol:** OpenFlow 1.3

---
## Problem Statement
In traditional networks, topology changes (link failures, new switches
joining) require manual monitoring. This project implements an SDN solution
using a Ryu controller that automatically detects and logs every topology
change in real time using OpenFlow 1.3 events.

The controller:
1.Detects switch join/leave via OpenFlow handshake events
2.Discovers links via LLDP-based topology discovery
3.Detects port state changes (up/down) via PortStatus messages
4.Implements an L2 learning switch with explicit match-action flow rules
5.Logs all changes with timestamps to topology_changes.log

---
## Topology
   h1            h2
    |             |
   [s1] -------- [s2]
    |  \         /
    |   \       /
   [s3]---------
   / \
  h3  h4
  (3 switches in a triangle (redundant paths), 4 hosts.  
Triangle chosen to demonstrate link failure with alternate path available.)

---
## Repository Structure


topology-detector/
├── topology_detector.py   # Ryu controller
├── custom_topology.py     # Mininet topology
├── screenshots/           # Proof of execution
└── README.md

---

## Setup & Execution

### Prerequisites

```bash
sudo apt install mininet python3-ryu -y
sudo pip3 install mininet
```

### Running

**Terminal 1 — Start Ryu controller:**
```bash
cd ~/topology-detector
python3 -m ryu.cmd.manager topology_detector.py --observe-links
```

**Terminal 2 — Start Mininet:**
```bash
cd ~/topology-detector
sudo python3 custom_topology.py
```

**Terminal 3 — Inspect:**
```bash
sudo ovs-ofctl -O OpenFlow13 dump-flows s1
tail -f topology_changes.log
```
---

## Expected Output

### Startup
Controller logs SWITCH_CONNECTED for each switch, then LINK_ADDED
for all 6 directed links as LLDP discovers the topology.

### Scenario 1 — Normal Operation
mininet> pingall
*** Results: 0% dropped (12/12 received)
### Scenario 2 — Link Failure Detection
mininet> link s1 s2 down
Controller immediately logs: PORT_MODIFIED  | switch=0x...1 port=2 state=DOWN
LINK_DELETED   | 0x...1:2 -> 0x...2:2
TOPOLOGY_UPDATE| 2 link(s) removed due to port down
Traffic reroutes via alternate path (s1→s3→s2).

---

## Proof of Execution

### Switch Connected & Links Discovered
![Switch connected](screenshots/01_switch_connected.png)
![Links added](screenshots/02_link_added.png)

### Scenario 1 — Connectivity
![Pingall](screenshots/03_pingall.png)
![Flow table s1](screenshots/04_flow_table_s1.png)
![iperf](screenshots/05_iperf.png)

### Scenario 2 — Link Failure & Recovery
![Link failure](screenshots/06_link_failure.png)
![Link restored](screenshots/07_link_restored.png)

### Topology Change Log
![Log file](screenshots/08_topology_log.png)

---

## References

1. Ryu documentation — https://ryu.readthedocs.io/
2. Mininet walkthrough — https://mininet.org/walkthrough/
3. OpenFlow 1.3 specification — https://opennetworking.org/wp-content/uploads/2014/10/openflow-spec-v1.3.0.pdf
4. Ryu topology API — https://github.com/faucetsdn/ryu/tree/master/ryu/topology
5. Open vSwitch documentation — https://docs.openvswitch.org/
