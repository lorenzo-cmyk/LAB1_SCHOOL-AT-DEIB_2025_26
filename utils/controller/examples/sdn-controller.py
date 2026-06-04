"""
SDN Controller — hop-by-hop routing with ARP proxy.

OBJECTIVE: modify this controller so that every forwarded IPv4 packet
           has its IP TTL set to 100.

This controller turns an OpenFlow network into a fully routed IP network.
When the controller starts, every switch is told "send all unknown packets
to me".  The controller then computes the shortest path across the topology
and installs forwarding rules hop by hop.

The topology is discovered automatically by OS-Ken's link observer, which
must be enabled with the ``--observe-links`` flag:

    os_ken-manager --observe-links sdn-controller.py

Flow of a packet through this controller:
1.  Switch receives a packet it has no rule for → sends Packet-In to controller.
2.  Controller looks up the destination host in the topology.
3.  Controller computes the shortest path from this switch to the destination.
4.  Controller tells the switch: "send this packet out port X, and remember
    this rule for future packets to this destination."
"""

from collections import deque
from os_ken.base import app_manager
from os_ken.controller import ofp_event
from os_ken.controller.handler import set_ev_cls, CONFIG_DISPATCHER, MAIN_DISPATCHER
from os_ken.ofproto import ofproto_v1_3
from os_ken.topology.api import get_all_link, get_all_host
from os_ken.lib.packet import packet, ethernet, ether_types, arp


class SDNController(app_manager.OSKenApp):
    """
    Hop-by-hop routing controller.

    Uses OS-Ken's topology discovery to build a graph of the network
    and computes shortest paths with BFS.  An ARP proxy answers ARP
    requests on behalf of known hosts so that every host can discover
    every other host's MAC address without broadcast flooding.
    """

    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    # ------------------------------------------------------------------
    #  _actions — the single place where forwarding actions are built.
    #
    #  Every time the controller tells a switch to send a packet somewhere,
    #  this method builds the list of OpenFlow actions.
    #
    #  EXERCISE: modify this method so that every forwarded IPv4 packet
    #            has its TTL set to 100.
    # ------------------------------------------------------------------

    def _actions(self, parser, output_port):
        """
        Build the list of OpenFlow actions for forwarding.
        Called by both:
          - OFPPacketOut (forward the *current* packet — line 207)
          - OFPFlowMod    (install a rule for *future* packets — line 217)
        """
        return [
            # parser.OFPActionSetNwTtl(nw_ttl=100),
            parser.OFPActionOutput(output_port),
        ]

    # ------------------------------------------------------------------
    #  switch_features_handler
    #
    #  Called once per switch, right after the OpenFlow handshake.
    #  Installs the *table-miss* flow: a catch-all rule with priority 0
    #  that sends every unmatched packet to the controller.
    #
    #  OFPP_CONTROLLER = virtual port that means "send to the controller"
    #  OFPCML_NO_BUFFER = do not store the packet on the switch; send the
    #                     full frame to the controller straight away
    # ------------------------------------------------------------------

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath        # the switch that just connected
        ofproto = datapath.ofproto        # OpenFlow protocol constants
        parser = datapath.ofproto_parser  # factory for building OF messages

        match = parser.OFPMatch()         # empty match → matches everything
        inst = [
            parser.OFPInstructionActions(
                ofproto.OFPIT_APPLY_ACTIONS,
                [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                         ofproto.OFPCML_NO_BUFFER)])
        ]
        mod = parser.OFPFlowMod(datapath=datapath, priority=0,
                                match=match, instructions=inst)
        datapath.send_msg(mod)

    # ------------------------------------------------------------------
    #  Topology helpers
    # ------------------------------------------------------------------

    def _find_host(self, mac):
        """
        Look up *mac* in the topology host table.
        Returns (switch_dpid, switch_port) or (None, None) if not found.
        """
        for host in get_all_host(self):
            if host.mac == mac:
                return (host.port.dpid, host.port.port_no)
        return (None, None)

    def _next_port(self, src_dpid, dst_dpid):
        """
        Compute the shortest path from *src_dpid* to *dst_dpid* using
        the link topology, then return the output port on *src_dpid*
        that leads toward *dst_dpid*.

        Uses BFS (breadth-first search) so the path has the minimum
        number of hops.  Returns None if no path exists.
        """
        # Build adjacency list from the link table.
        # Each link knows which port on the source switch connects to
        # which destination switch.  LLDP discovers links in both
        # directions, so we get a full picture of the topology.
        graph = {}
        for link in get_all_link(self):
            graph.setdefault(link.src.dpid, {})[link.dst.dpid] = link.src.port_no

        # BFS to find the shortest path (fewest switches)
        queue = deque([src_dpid])
        prev = {src_dpid: None}
        while queue:
            u = queue.popleft()
            if u == dst_dpid:
                break
            for v in graph.get(u, {}):
                if v not in prev:
                    prev[v] = u
                    queue.append(v)

        if dst_dpid not in prev:
            return None                      # no path

        # Walk backwards from dst to find the first hop after src
        cur = dst_dpid
        while prev[cur] != src_dpid:
            cur = prev[cur]
        return graph[src_dpid][cur]

    # ------------------------------------------------------------------
    #  PacketIn handler — the core of the controller
    #
    #  Fires every time a switch sends a packet to the controller
    #  (because the table-miss rule matched it).
    #
    #  The handler decides what to do with the packet:
    #    - LLDP packets     → ignore (topology probes)
    #    - ARP packets      → handle via ARP proxy
    #    - IPv4 packets     → compute path, forward, install rule
    #    - everything else  → ignore
    # ------------------------------------------------------------------

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']    # physical port the packet arrived on

        # Parse the raw bytes into a structured Ethernet frame
        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)

        # Ignore LLDP — these are topology-discovery probes sent by OS-Ken.
        # Forwarding them would cause loops.
        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            return

        # Delegate ARP to the proxy
        if eth.ethertype == ether_types.ETH_TYPE_ARP:
            self._proxy_arp(msg)
            return

        # Only route IPv4 packets; ignore everything else
        if eth.ethertype != ether_types.ETH_TYPE_IP:
            return

        # ---- Look up the destination host ----
        dst_mac = eth.dst
        dst_dpid, dst_port = self._find_host(dst_mac)
        if dst_dpid is None:
            self.logger.debug("Host %s not yet discovered", dst_mac)
            return

        # ---- Choose the output port ----
        if dst_dpid == datapath.id:
            out_port = dst_port      # host is directly attached to this switch
        else:
            out_port = self._next_port(datapath.id, dst_dpid)
            if out_port is None:
                self.logger.debug("No path %s → %s", datapath.id, dst_dpid)
                return

        # ---- Forward the *current* packet ----
        # OFPPacketOut tells the switch: "inject this raw data out of out_port"
        actions = self._actions(parser, out_port)
        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                  in_port=in_port, actions=actions,
                                  data=msg.data)
        datapath.send_msg(out)

        # ---- Install a *flow rule* for future packets ----
        # Now that we know the path, tell the switch to handle matching
        # packets on its own, without asking the controller again.
        # idle_timeout=60 means the rule is removed after 60s of no
        # traffic, keeping the flow table small.
        match = parser.OFPMatch(eth_dst=dst_mac)
        inst = [
            parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                         self._actions(parser, out_port))
        ]
        mod = parser.OFPFlowMod(datapath=datapath, priority=10, match=match,
                                instructions=inst, idle_timeout=60)
        datapath.send_msg(mod)

    # ------------------------------------------------------------------
    #  ARP proxy
    #
    #  ARP (Address Resolution Protocol) is how hosts ask "who has this
    #  IP?".  Normally the question is broadcast everywhere and the
    #  target answers.  Since our controller already knows every host
    #  (from topology discovery), it can answer directly on the target's
    #  behalf — no broadcast needed.
    # ------------------------------------------------------------------

    def _proxy_arp(self, msg):
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']

        pkt_in = packet.Packet(msg.data)
        eth_in = pkt_in.get_protocol(ethernet.ethernet)
        arp_in = pkt_in.get_protocol(arp.arp)

        # We only proxy ARP REQUEST (opcode 1).  REPLIES are forwarded
        # normally by the switch pipeline.
        if arp_in.opcode != arp.ARP_REQUEST:
            return

        # Find the target host by IP in the topology table.
        # host.ipv4 is a list of IPv4 addresses of that host.
        dst_mac = None
        for host in get_all_host(self):
            if arp_in.dst_ip in host.ipv4:
                dst_mac = host.mac
                break

        if dst_mac is None:
            return   # target unknown — let the request be flooded naturally

        # Build the ARP REPLY frame.
        # The reply says: "the MAC for IP *dst_ip* is *dst_mac*".
        # Ethernet src = target MAC (we are answering on its behalf)
        # Ethernet dst = requester MAC (the host that asked)
        pkt_out = packet.Packet()
        eth_out = ethernet.ethernet(dst=eth_in.src, src=dst_mac,
                                    ethertype=ether_types.ETH_TYPE_ARP)
        arp_out = arp.arp(opcode=arp.ARP_REPLY,
                          src_mac=dst_mac, src_ip=arp_in.dst_ip,
                          dst_mac=arp_in.src_mac, dst_ip=arp_in.src_ip)
        pkt_out.add_protocol(eth_out)
        pkt_out.add_protocol(arp_out)
        pkt_out.serialize()    # convert to raw bytes

        # Send the reply back through the port the request came from
        out = parser.OFPPacketOut(datapath=datapath,
                                  buffer_id=ofproto.OFP_NO_BUFFER,
                                  in_port=ofproto.OFPP_CONTROLLER,
                                  actions=[parser.OFPActionOutput(in_port)],
                                  data=pkt_out.data)
        datapath.send_msg(out)
