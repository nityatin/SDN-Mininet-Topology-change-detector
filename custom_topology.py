# custom_topology.py
# Mininet topology for SDN Topology Change Detector
# Topology:
    # 3 Switches in a Triangle: s1 -- s2 -- s3 -- s1  (redundant paths)
    # 4 Hosts: h1@s1, h2@s2, h3@s3, h4@s3
    # Remote Ryu controller on 127.0.0.1:6653


from mininet.net    import Mininet
from mininet.node   import RemoteController, OVSKernelSwitch
from mininet.cli    import CLI
from mininet.log    import setLogLevel, info
from mininet.link   import TCLink


def build_topology():
    """Build and launch the triangle topology."""

    net = Mininet(
        controller=RemoteController,
        switch=OVSKernelSwitch,
        link=TCLink,
        autoSetMacs=True       # assign predictable MACs
    )

    # ── Controller ──────────────────────────────────────────────
    info('*** Adding remote controller (Ryu on 127.0.0.1:6653)\n')
    c0 = net.addController(
        'c0',
        controller=RemoteController,
        ip='127.0.0.1',
        port=6653
    )

    # ── Switches ────────────────────────────────────────────────
    info('*** Adding switches\n')
    s1 = net.addSwitch('s1', dpid='0000000000000001')
    s2 = net.addSwitch('s2', dpid='0000000000000002')
    s3 = net.addSwitch('s3', dpid='0000000000000003')

    # ── Hosts ────────────────────────────────────────────────────
    info('*** Adding hosts\n')
    h1 = net.addHost('h1', ip='10.0.0.1/24')
    h2 = net.addHost('h2', ip='10.0.0.2/24')
    h3 = net.addHost('h3', ip='10.0.0.3/24')
    h4 = net.addHost('h4', ip='10.0.0.4/24')

    # ── Links ─────────────────────────────────────────────────────
    # Host links
    info('*** Adding links\n')
    net.addLink(h1, s1)
    net.addLink(h2, s2)
    net.addLink(h3, s3)
    net.addLink(h4, s3)

    # Switch-to-switch links (triangle)
    net.addLink(s1, s2, bw=10)   # 10 Mbps
    net.addLink(s2, s3, bw=10)
    net.addLink(s1, s3, bw=10)   # redundant path

    # ── Start ─────────────────────────────────────────────────────
    info('*** Starting network\n')
    net.build()
    c0.start()
    for sw in [s1, s2, s3]:
        sw.start([c0])

    # Set OvS to OpenFlow 1.3
    for sw in [s1, s2, s3]:
        sw.cmd(f'ovs-vsctl set bridge {sw.name} protocols=OpenFlow13')

    info('*** Network started — launching CLI\n')
    info('*** Topology: h1-s1-s2-h2, s2-s3-h3,h4, s1-s3 (triangle)\n')
    CLI(net)

    info('*** Stopping network\n')
    net.stop()


if __name__ == '__main__':
    setLogLevel('info')
    build_topology()
