# topology_detector.py - FIXED VERSION

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import (
    CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
)
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet, ether_types
from ryu.topology import event as topo_event
from ryu.topology.api import get_switch, get_link
import logging
import datetime


class TopologyChangeDetector(app_manager.RyuApp):

    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(TopologyChangeDetector, self).__init__(*args, **kwargs)
        self.mac_to_port = {}
        self.topology_map = {
            'switches': {},
            'links': [],
        }
        self.change_log = []

        # ports that connect to OTHER switches (not hosts)
        # we avoid learning MACs on these ports
        self.switch_ports = {}

        file_handler = logging.FileHandler('topology_changes.log')
        file_handler.setFormatter(
            logging.Formatter('%(asctime)s  %(message)s')
        )
        self.topo_logger = logging.getLogger('topo')
        self.topo_logger.setLevel(logging.INFO)
        self.topo_logger.addHandler(file_handler)
        self.logger.info("=== Topology Change Detector Started ===")

    def log_change(self, event_type, details):
        ts = datetime.datetime.now().strftime('%H:%M:%S.%f')[:-3]
        line = f"[{ts}] {event_type:<20s} | {details}"
        self.change_log.append(line)
        self.logger.info(line)
        self.topo_logger.info(f"{event_type} | {details}")
        self._print_topology()

    def _print_topology(self):
        sw_list = list(self.topology_map['switches'].keys())
        link_count = len(self.topology_map['links'])
        self.logger.info(f"  ▸ Switches: {sw_list}")
        self.logger.info(f"  ▸ Links   : {link_count} active")

    def add_flow(self, datapath, priority, match, actions, buffer_id=None):
        ofproto = datapath.ofproto
        parser  = datapath.ofproto_parser
        inst = [parser.OFPInstructionActions(
            ofproto.OFPIT_APPLY_ACTIONS, actions
        )]
        kwargs = dict(
            datapath=datapath,
            priority=priority,
            match=match,
            instructions=inst
        )
        if buffer_id is not None:
            kwargs['buffer_id'] = buffer_id
        datapath.send_msg(parser.OFPFlowMod(**kwargs))

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto  = datapath.ofproto
        parser   = datapath.ofproto_parser
        dpid     = datapath.id

        match   = parser.OFPMatch()
        actions = [parser.OFPActionOutput(
            ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER
        )]
        self.add_flow(datapath, priority=0, match=match, actions=actions)

        self.mac_to_port.setdefault(dpid, {})
        self.switch_ports.setdefault(dpid, set())
        self.topology_map['switches'][f"{dpid:#018x}"] = {
            'ports': [], 'active': True
        }
        self.log_change(
            'SWITCH_CONNECTED',
            f"dpid={dpid:#018x} — table-miss flow installed"
        )

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        msg      = ev.msg
        datapath = msg.datapath
        ofproto  = datapath.ofproto
        parser   = datapath.ofproto_parser
        in_port  = msg.match['in_port']
        dpid     = datapath.id

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]

        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            return

        src, dst = eth.src, eth.dst
        self.mac_to_port.setdefault(dpid, {})
        self.switch_ports.setdefault(dpid, set())

        # Only learn MAC if the packet came from a HOST port (not a switch port)
        if in_port not in self.switch_ports[dpid]:
            self.mac_to_port[dpid][src] = in_port

        # Forwarding decision
        if dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst]
        else:
            out_port = ofproto.OFPP_FLOOD

        actions = [parser.OFPActionOutput(out_port)]

        if out_port != ofproto.OFPP_FLOOD:
            match = parser.OFPMatch(
                in_port=in_port,
                eth_dst=dst,
                eth_src=src
            )
            if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                self.add_flow(datapath, priority=1, match=match,
                              actions=actions, buffer_id=msg.buffer_id)
                return
            else:
                self.add_flow(datapath, priority=1, match=match,
                              actions=actions)

        data = msg.data if msg.buffer_id == ofproto.OFP_NO_BUFFER else None
        out = parser.OFPPacketOut(
            datapath=datapath,
            buffer_id=msg.buffer_id,
            in_port=in_port,
            actions=actions,
            data=data
        )
        datapath.send_msg(out)

    @set_ev_cls(ofp_event.EventOFPPortStatus, MAIN_DISPATCHER)
    def port_status_handler(self, ev):
        msg     = ev.msg
        dp      = msg.datapath
        ofproto = dp.ofproto
        port    = msg.desc
        dpid    = dp.id

        reason_map = {
            ofproto.OFPPR_ADD:    'PORT_ADDED',
            ofproto.OFPPR_DELETE: 'PORT_DELETED',
            ofproto.OFPPR_MODIFY: 'PORT_MODIFIED',
        }
        reason     = reason_map.get(msg.reason, 'UNKNOWN')
        port_state = 'DOWN' if (port.state & ofproto.OFPPS_LINK_DOWN) else 'UP'
        port_name  = port.name.decode('utf-8', errors='replace')

        self.log_change(
            reason,
            f"switch={dpid:#018x} port={port.port_no}"
            f" name={port_name} state={port_state}"
        )

        if reason == 'PORT_MODIFIED' and port_state == 'DOWN':
            before = len(self.topology_map['links'])
            self.topology_map['links'] = [
                l for l in self.topology_map['links']
                if not (
                    (l[0] == dpid and l[1] == port.port_no) or
                    (l[2] == dpid and l[3] == port.port_no)
                )
            ]
            removed = before - len(self.topology_map['links'])
            if removed:
                self.log_change(
                    'TOPOLOGY_UPDATE',
                    f"{removed} link(s) removed due to port down"
                )

    @set_ev_cls(topo_event.EventSwitchEnter)
    def switch_enter_handler(self, ev):
        sw   = ev.switch
        dpid = sw.dp.id
        ports = [p.port_no for p in sw.ports]
        self.topology_map['switches'][f"{dpid:#018x}"] = {
            'ports': ports, 'active': True
        }
        self.log_change('SWITCH_ENTER',
                        f"dpid={dpid:#018x} ports={ports}")

    @set_ev_cls(topo_event.EventSwitchLeave)
    def switch_leave_handler(self, ev):
        dpid = ev.switch.dp.id
        key  = f"{dpid:#018x}"
        if key in self.topology_map['switches']:
            self.topology_map['switches'][key]['active'] = False
        self.log_change('SWITCH_LEAVE',
                        f"dpid={dpid:#018x} disconnected")

    @set_ev_cls(topo_event.EventLinkAdd)
    def link_add_handler(self, ev):
        src = ev.link.src
        dst = ev.link.dst
        entry = (src.dpid, src.port_no, dst.dpid, dst.port_no)
        if entry not in self.topology_map['links']:
            self.topology_map['links'].append(entry)

        # Register these as switch-to-switch ports so we don't
        # learn host MACs on them
        self.switch_ports.setdefault(src.dpid, set()).add(src.port_no)
        self.switch_ports.setdefault(dst.dpid, set()).add(dst.port_no)

        self.log_change('LINK_ADDED',
            f"{src.dpid:#018x}:{src.port_no}"
            f" -> {dst.dpid:#018x}:{dst.port_no}")

    @set_ev_cls(topo_event.EventLinkDelete)
    def link_delete_handler(self, ev):
        src = ev.link.src
        dst = ev.link.dst
        entry = (src.dpid, src.port_no, dst.dpid, dst.port_no)
        if entry in self.topology_map['links']:
            self.topology_map['links'].remove(entry)
        self.log_change('LINK_DELETED',
            f"{src.dpid:#018x}:{src.port_no}"
            f" -> {dst.dpid:#018x}:{dst.port_no}")
