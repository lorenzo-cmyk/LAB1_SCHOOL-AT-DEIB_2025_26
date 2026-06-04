# Copyright (c) 2018-2026 Maen Artimy
#
# SDN Controller — an L2 learning switch with ARP proxy built on OS-Ken.
#
# OS-Ken is a Software-Defined Networking framework that acts as an OpenFlow
# controller.  It speaks the OpenFlow protocol (v1.3 here) to programmable
# switches in the network.  The controller receives events (e.g. "a switch
# connected", "a packet arrived that the switch didn't know how to handle")
# and responds by installing *flow entries* — rules in the switch's hardware
# tables that tell it how to forward future packets at line rate.
#
# This file implements one OS-Ken *application*.  The framework
# auto-discovers every class that extends ``OSKenApp`` and hooks its event
# handlers into the OpenFlow message loop.
#
# Architecture of this controller
# -------------------------------
# The switch pipeline has three OpenFlow tables:
#
#   Table 0  —  LEARN_TABLE
#       Checks:  "did this packet arrive on the port we learned for its
#                 source MAC?"
#       Action:  if yes → goto Table 1  (trusted, skip the controller)
#                if no  → copy to controller + goto Table 1
#
#   Table 1  —  TTL_TABLE   *** STUDENT EXERCISE — modify this table ***
#       Checks:  "is this an IPv4 or IPv6 packet?"
#       Action:  if yes → set TTL / Hop-Limit to 100, then goto Table 2
#                if no  → goto Table 2 directly (no TTL change)
#
#   Table 2  —  FORWARD_TABLE
#       Checks:  "do I already know which port leads to this destination
#                 MAC?"
#       Action:  known   → send out that port
#                unknown → flood to all ports
#
# Additionally, this controller runs an **ARP proxy**: when a host sends
# "who has 10.0.0.2?", if the controller already knows 10.0.0.2's MAC it
# answers directly, avoiding the need to flood the ARP request across the
# network.  This guarantees L2 continuity on any topology.

from os_ken.base import app_manager        # base class for all OS-Ken apps
from os_ken.controller import ofp_event    # OpenFlow protocol event types
from os_ken.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from os_ken.controller.handler import set_ev_cls   # decorator: "call this on event X"
from os_ken.ofproto import ofproto_v1_3    # OpenFlow 1.3 constants & data-structures
from os_ken.lib.packet import packet        # generic packet (de)serialisation
from os_ken.lib.packet import ethernet      # Ethernet header
from os_ken.lib.packet import ether_types   # Ethertype constants (0x0800, 0x0806, etc.)
from os_ken.lib.packet import arp           # ARP header
from base_switch import BaseSwitch          # helper: add_flow, del_flow, send_messages

# ---------------------------------------------------------------------------
#  Pipeline table IDs — must match the hardware tables on the OpenFlow switch
# ---------------------------------------------------------------------------
LEARN_TABLE = 0          # table 0: validate source MAC / port
TTL_TABLE = 1            # table 1: apply IP TTL override (student exercise)
FORWARD_TABLE = 2        # table 2: choose output port

# ---------------------------------------------------------------------------
#  Flow entry priorities (higher = matched first)
# ---------------------------------------------------------------------------
LOW_PRIORITY = 0         # table-miss  — matches when nothing more specific does
MID_PRIORITY = 100        # learned MAC — specific (MAC, port) entries
TOP_PRIORITY = 300        # overrides   — IP-matching TTL rules, etc.


class SDNController(BaseSwitch):
    """
    An L2 learning switch with ARP proxy and configurable TTL override.

    **What this controller does**
      - Learns source MAC addresses from incoming packets.
      - Installs reactive forwarding rules so future packets are
        hardware-switched.
      - Proxies ARP replies when the target host is already known,
        providing L2 connectivity across any topology (linear, tree,
        mesh, ring, …) without relying on broadcast flooding.
      - Sets the IPv4 TTL and IPv6 Hop Limit to 100 on ALL switched
        IP traffic (Table 1).  The student's exercise is to remove
        or modify this behaviour.
    """

    # Tell OS-Ken which OpenFlow version we speak (1.3)
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # --- Learning tables (per-datapath) ---
        #
        #   ip_to_mac   :  dpid → { ip_addr → (mac_addr, port) }
        #       Populated by ARP and used for ARP proxy lookups.
        #
        #   mac_to_port :  dpid → { mac_addr  → port }
        #       Standard L2 MAC table (kept for reference; reactive
        #       rules are the source of truth in the forwarding pipeline).
        #
        self.ip_to_mac = {}
        self.mac_to_port = {}

    # ==================================================================
    #  _build_forward_actions
    # ==================================================================
    #
    # Every time this controller tells a switch "send packet X out
    # port Y", the action list is built right here.  The forwarding
    # action is always just a plain ``Output`` — all packet
    # modifications (like TTL override) happen in Table 1 before the
    # packet ever reaches the forwarding table.
    #
    # If you wanted to apply additional actions to forwarded packets
    # (beyond what Table 1 already does), this is the single place
    # to edit.
    #
    def _build_forward_actions(self, parser, output_port):
        """
        Build the list of OpenFlow actions that forward a packet out
        of ``output_port``.

        Parameters
        ----------
        parser : module
            The switch's OF proto parser (e.g. ``ofproto_v1_3_parser``).
        output_port : int
            The switch port number to send the packet to, or a virtual
            port constant such as ``OFPP_FLOOD``.

        Returns
        -------
        list of OFPAction
            Actions to be applied, in order, to the packet.
        """
        # Plain forwarding.  TTL and other packet modifications are
        # applied upstream in the TTL_TABLE pipeline stage.
        return [parser.OFPActionOutput(output_port)]

    # ==================================================================
    #  Learning helpers
    # ==================================================================

    def _learn_mac(self, dpid, mac, port):
        """Record that *mac* was seen on *port* of switch *dpid*."""
        # ``setdefault`` creates the inner dict on first use per switch
        self.mac_to_port.setdefault(dpid, {})[mac] = port

    def _learn_ip(self, dpid, ip_addr, mac, port):
        """Record IP→(MAC, port) mapping from an ARP packet."""
        self.ip_to_mac.setdefault(dpid, {})[ip_addr] = (mac, port)
        self._learn_mac(dpid, mac, port)

    # ==================================================================
    #  Event handler 1 — switch connected (configuration phase)
    # ==================================================================
    #
    # This fires once per switch right after the OpenFlow handshake
    # completes (``CONFIG_DISPATCHER`` state).  We wipe any stale
    # flows and install the three table-miss entries — the catch-all
    # rules that decide what happens when no specific rule matches.
    #
    # ``@set_ev_cls`` is the OS-Ken decorator that says "call this
    # method when the given event arrives".
    #

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        """
        Install the pipeline's table-miss flow entries.

        Called every time a switch finishes the OpenFlow handshake:
          1. Delete all existing flows on the switch (clean slate).
          2. Install the three table-miss rules.
          3. Install the TTL-override rules in Table 1.
        """

        # ---- Aliases to keep the code compact ----
        datapath = ev.msg.datapath            # the switch object
        ofproto = datapath.ofproto            # OpenFlow protocol constants
        parser = datapath.ofproto_parser      # factory for OF messages
        dpid = datapath.id                    # unique switch ID (datapath ID)

        # ---------- 1. Clear the switch ----------
        msgs = [self.del_flow(datapath)]

        # ---------- 2.  LEARN_TABLE  table-miss  (table 0) ----------
        #
        # ``OFPMatch()`` with no arguments → matches EVERY packet
        # (that hasn't been matched by a higher-priority rule).
        #
        # Two instructions are applied in order:
        #   a) Apply-Actions: output to CONTROLLER with NO_BUFFER.
        #      NO_BUFFER means "don't buffer the packet on the
        #      switch, send the full data to the controller".  The
        #      original packet continues down the pipeline.
        #   b) Goto-Table: jump to TTL_TABLE for the next
        #      lookup.
        #
        match = parser.OFPMatch()
        actions = [
            parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                   ofproto.OFPCML_NO_BUFFER)
        ]
        inst = [
            parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                         actions),
            parser.OFPInstructionGotoTable(TTL_TABLE),
        ]
        msgs += [self.add_flow(datapath, LEARN_TABLE, LOW_PRIORITY,
                               match, inst)]

        # ---------- 3.  TTL_TABLE  entries  (table 1) ----------
        #
        # This table exists exclusively to give students a simple,
        # centralised place to modify packet headers before
        # forwarding.  Every packet passes through here on its way
        # from LEARN_TABLE to FORWARD_TABLE.
        #
        # The two TOP_PRIORITY rules below intercept IPv4 (ethertype
        # 0x0800) and IPv6 (ethertype 0x86DD) packets and overwrite
        # their TTL / Hop Limit to 100.  Non-IP packets (ARP, LLDP,
        # etc.) fall through to the table-miss and are forwarded
        # unchanged.
        #
        # ─── STUDENT EXERCISE ─────────────────────────────────────
        # To disable the TTL override, delete the two blocks
        # (IPv4 + IPv6) below — two delete operations.
        # To change the TTL value, edit ``nw_ttl=100`` in both blocks.
        # The edit requires  ≤2  lines of change.
        # ───────────────────────────────────────────────────────────
        #
        # The ``OFPAT_SET_NW_TTL`` action was introduced in OpenFlow
        # 1.0 and is still valid in 1.3.  ``nw`` stands for
        # "network" (layer-3).  It modifies the IPv4 TTL field and
        # the IPv6 Hop Limit field in one go.

        # -- IPv4 TTL override (ethertype 0x0800) --
        match = parser.OFPMatch(eth_type=0x0800)
        actions = [parser.OFPActionSetNwTtl(nw_ttl=100)]
        inst = [
            parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                         actions),
            parser.OFPInstructionGotoTable(FORWARD_TABLE),
        ]
        msgs += [self.add_flow(datapath, TTL_TABLE, TOP_PRIORITY,
                               match, inst)]

        # -- IPv6 Hop Limit override (ethertype 0x86DD) --
        match = parser.OFPMatch(eth_type=0x86DD)
        actions = [parser.OFPActionSetNwTtl(nw_ttl=100)]
        inst = [
            parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                         actions),
            parser.OFPInstructionGotoTable(FORWARD_TABLE),
        ]
        msgs += [self.add_flow(datapath, TTL_TABLE, TOP_PRIORITY,
                               match, inst)]

        # -- TTL_TABLE  table-miss (non-IP packets) --
        # Everything else (ARP, LLDP, …) skips straight to
        # FORWARD_TABLE with no modification.
        match = parser.OFPMatch()
        inst = [parser.OFPInstructionGotoTable(FORWARD_TABLE)]
        msgs += [self.add_flow(datapath, TTL_TABLE, LOW_PRIORITY,
                               match, inst)]

        # ---------- 4.  FORWARD_TABLE  table-miss  (table 2) ----------
        #
        # Any packet that reaches this entry was not matched by a
        # learned MAC → port rule.  The only safe action is to
        # flood it (send it out every port except the one it
        # arrived on) so it eventually reaches its destination.
        #
        match = parser.OFPMatch()
        actions = self._build_forward_actions(parser, ofproto.OFPP_FLOOD)
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        msgs += [self.add_flow(datapath, FORWARD_TABLE, LOW_PRIORITY,
                               match, inst)]

        # Push all the FlowMod messages to the switch
        self.send_messages(datapath, msgs)

    # ==================================================================
    #  Event handler 2 — Packet-In (the switch asks for help)
    # ==================================================================
    #
    # When a packet hits the Table-0 table-miss, the switch sends a
    # copy to the controller (Packet-In message) while the original
    # packet continues to Table 1 and then to Table 2 (where it is
    # flooded if still unknown).
    #
    # The job inside this handler is to **learn** so that *future*
    # packets of the same flow don't need the controller.
    #

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        """
        Process a Packet-In: learn source MAC, handle ARP, and install
        reactive forwarding rules for subsequent packets.
        """

        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        dpid = datapath.id

        # The switch tells us which physical port the packet arrived on
        in_port = ev.msg.match["in_port"]

        # Deserialise the raw bytes into a structured packet
        pkt = packet.Packet(ev.msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)

        # Ignore LLDP (Link-Layer Discovery Protocol) — these are
        # topology-discovery probes sent by OS-Ken's link observer
        # (``--observe-links`` flag).  We must not forward them.
        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            return

        src, dst = eth.src, eth.dst

        # Always learn the source MAC → port mapping.
        # Learning early means we can use it later, including inside
        # the ARP handler.
        self._learn_mac(dpid, src, in_port)

        # ---- ARP branch (ethertype 0x0806) ----
        # ARP is how IPv4 hosts discover each other's hardware
        # (MAC) addresses.  "who has 10.0.0.2? tell 10.0.0.1".
        # We intercept these requests and proxy the reply when we
        # already know the answer.
        if eth.ethertype == ether_types.ETH_TYPE_ARP:
            self._handle_arp(datapath, in_port, pkt, eth, src)
            return

        # ---- Non-ARP: standard reactive learning switch ----
        self.logger.info("packet in %s %s %s %s", dpid, src, dst, in_port)

        # --- Rule 1 — LEARN_TABLE  (table 0) ---
        # Match:      ``in_port == <learned port> AND eth_src == <MAC>``
        # Action:     goto TTL_TABLE
        # Effect:     "if a frame from this MAC arrives on this port
        #              again, trust it and skip the controller."
        # Idle timeout: 30 s  → rule is removed if no matching traffic
        #                       for 30 seconds (keeps the table small).
        #
        match = parser.OFPMatch(in_port=in_port, eth_src=src)
        inst = [parser.OFPInstructionGotoTable(TTL_TABLE)]
        msgs = [self.add_flow(datapath, LEARN_TABLE, MID_PRIORITY,
                              match, inst, i_time=30)]

        # --- Rule 2 — FORWARD_TABLE  (table 2) ---
        # Match:      ``eth_dst == <MAC>``
        # Action:     output to <port>
        # Effect:     "packets destined for this MAC go straight out
        #              the learned port — no more flooding."
        # Idle timeout: 40 s
        #
        # Note: this rule's output goes through TTL_TABLE first (it
        #       got here via GotoTable), so the TTL override has
        #       already been applied by the time this rule runs.
        #
        match = parser.OFPMatch(eth_dst=src)
        actions = self._build_forward_actions(parser, in_port)
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        msgs += [self.add_flow(datapath, FORWARD_TABLE, MID_PRIORITY,
                               match, inst, i_time=40)]

        self.send_messages(datapath, msgs)

    # ==================================================================
    #  ARP proxy  —  answer "who-has" when we already know
    # ==================================================================
    #
    # Why ARP proxy?
    #   In a traditional network ARP requests are broadcast and every
    #   host sees them.  In SDN we can do better: the controller
    #   already knows every IP → MAC → port mapping (because it sees
    #   ALL ARP traffic), so it can answer on behalf of the target.
    #   This:
    #     • eliminates ARP broadcast storms in large / mesh topologies,
    #     • provides instant resolution (no 1-3 second ARP timeout wait),
    #     • works regardless of network shape.
    #
    def _handle_arp(self, datapath, in_port, pkt, eth, src):
        """
        Handle an incoming ARP packet.

        Always learns IP→MAC from every ARP packet (request and
        reply) so the proxy stays up-to-date.

        If it is an ARP REQUEST and we already know the target's
        (IP, MAC, port) mapping, we:
          1. Proactively install bidirectional forwarding rules so
             subsequent unicast traffic is hardware-switched.
          2. Construct and send an ARP REPLY on behalf of the target.
        """

        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        dpid = datapath.id

        # Extract the ARP layer from the packet
        arp_pkt = pkt.get_protocol(arp.arp)
        if arp_pkt is None:
            return

        # Friendly names from the ARP header
        src_ip, src_mac = arp_pkt.src_ip, arp_pkt.src_mac

        # Always learn the sender — replies teach us the target's
        # IP→MAC just as well as requests do.  If we skip replies
        # we never learn hosts that don't initiate ARP themselves,
        # and the proxy breaks for them.
        self._learn_ip(dpid, src_ip, src_mac, in_port)

        # Only proxy on requests (opcode 1).  Replies (opcode 2) and
        # gratuitous ARP are already handled naturally by the pipeline.
        if arp_pkt.opcode != arp.ARP_REQUEST:
            return

        dst_ip = arp_pkt.dst_ip

        self.logger.info("ARP request %s: who-has %s? tell %s",
                         dpid, dst_ip, src_ip)

        # If we don't know the target IP, do nothing.  The original
        # ARP request will still be flooded by the Table-2 table-miss
        # and the target can answer naturally.
        if dst_ip not in self.ip_to_mac.get(dpid, {}):
            return

        target_mac, target_port = self.ip_to_mac[dpid][dst_ip]

        # ===========================================================
        #  Proactive flow installation
        # ===========================================================
        # At this point both the requester AND the target are known.
        # Install bidirectional forwarding rules so the subsequent
        # unicast stream never touches the controller.
        #
        msgs = []

        # A → B  direction:  eth_dst == target_mac → output target_port
        match = parser.OFPMatch(eth_dst=target_mac)
        actions = self._build_forward_actions(parser, target_port)
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        msgs += [self.add_flow(datapath, FORWARD_TABLE, MID_PRIORITY,
                               match, inst, i_time=60)]

        # B → A  direction:  eth_dst == src_mac    → output in_port
        match = parser.OFPMatch(eth_dst=src_mac)
        actions = self._build_forward_actions(parser, in_port)
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        msgs += [self.add_flow(datapath, FORWARD_TABLE, MID_PRIORITY,
                               match, inst, i_time=60)]

        self.send_messages(datapath, msgs)

        # ===========================================================
        #  Build and send the ARP REPLY
        # ===========================================================
        # We respond ON BEHALF OF the target host, so:
        #   • Ethernet  src  →  target_mac  (the MAC we are proxying)
        #   • Ethernet  dst  →  src_mac     (the requester)
        #   • ARP       src_mac → target_mac
        #   • ARP       src_ip  → dst_ip    (the IP being asked about)
        #   • ARP       dst_mac → src_mac
        #   • ARP       dst_ip  → src_ip
        #
        # Note: src_mac/dst_mac in the Ethernet header MUST match
        #       src_mac/dst_mac in the ARP payload.  Using different
        #       values confuses host OS ARP caches.
        #
        e = ethernet.ethernet(dst=src_mac,
                              src=target_mac,
                              ethertype=ether_types.ETH_TYPE_ARP)
        a = arp.arp(opcode=arp.ARP_REPLY,
                    src_mac=target_mac,
                    src_ip=dst_ip,
                    dst_mac=src_mac,
                    dst_ip=src_ip)

        # Assemble the packet into a raw buffer
        reply = packet.Packet()
        reply.add_protocol(e)
        reply.add_protocol(a)
        reply.serialize()          # convert to bytes

        # Send the reply back to the port the request came from.
        # ``OFPPacketOut`` tells the switch "inject this raw packet
        # into the data-plane on port *in_port*".
        po_actions = [parser.OFPActionOutput(in_port)]
        out = parser.OFPPacketOut(datapath=datapath,
                                  buffer_id=ofproto.OFP_NO_BUFFER,
                                  in_port=ofproto.OFPP_CONTROLLER,
                                  actions=po_actions,
                                  data=reply.data)
        datapath.send_msg(out)

        self.logger.info("ARP proxy  %s: %s is-at %s (port %s)",
                         dpid, dst_ip, target_mac, target_port)
