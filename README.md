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
<img width="950" height="893" alt="ryu-manager ss" src="https://github.com/user-attachments/assets/a47a2e65-e9ba-476f-9af9-d975e3c32764" />

### Starting Mininet and Topology
<img width="1478" height="356" alt="mininet startup" src="https://github.com/user-attachments/assets/02f75928-c7e2-4828-889d-c111e756d3d2" />

### Scenario 1 — Connectivity
Pingall and Ping statistics 
<img width="1117" height="828" alt="ping" src="https://github.com/user-attachments/assets/325b4339-2ac5-4bb4-8f85-8e714a68c016" />

Flow Tables
<img width="1854" height="325" alt="flow tables_final" src="https://github.com/user-attachments/assets/3001f592-7183-41cc-87cc-6c7261b17f45" />

iperf
<img width="744" height="96" alt="iperf1" src="https://github.com/user-attachments/assets/3a536713-2a4a-47a0-917d-930b2e8f59d0" />


### Scenario 2 — Link Failure & Recovery
<img width="372" height="36" alt="links1s2down" src="https://github.com/user-attachments/assets/5043abb8-b498-4649-9259-6cef09fb40c5" />

<img width="845" height="442" alt="link failure scenario_deltet" src="https://github.com/user-attachments/assets/f5f71581-e982-4825-84db-bda81c990448" />
Now recovering the lost links:
<img width="672" height="58" alt="links1s2UP" src="https://github.com/user-attachments/assets/5f241ded-d8fc-4e31-8031-a92ba0905757" />

<img width="765" height="268" alt="link failure scenario_add" src="https://github.com/user-attachments/assets/bd37c302-e75c-41a7-a0e1-eccef0ef058b" />

### Topology Change Log
<img width="1066" height="923" alt="topo change logs" src="https://github.com/user-attachments/assets/a3e4a4c0-9322-4373-8eb7-ab7a787edf25" />


---

## References

1. Ryu documentation — https://ryu.readthedocs.io/
2. Mininet walkthrough — https://mininet.org/walkthrough/
3. OpenFlow 1.3 specification — https://opennetworking.org/wp-content/uploads/2014/10/openflow-spec-v1.3.0.pdf
4. Ryu topology API — https://github.com/faucetsdn/ryu/tree/master/ryu/topology
5. Open vSwitch documentation — https://docs.openvswitch.org/
