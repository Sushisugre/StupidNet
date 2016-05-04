from pox.core import core
import pox.openflow.libopenflow_01 as of
from pox.lib.addresses import IPAddr, EthAddr
from pox.lib.util import dpid_to_str
import pox.lib.packet as pkt
import threading


log = core.getLogger()


class Mixnet(object):
    """ Todo """
    def __init__ (self, connection, balancer_addr):
        # Keep track of the connection to the switch     
        self.connection = connection
        # This binds our PacketIn event listener
        connection.addListeners(self)
        self.flow_map = {}
        self.mac = EthAddr("01:01:01:01:01:01")
        self.ip = IPAddr(balancer_addr)
        self.clients = []

    def send_packet (self, packet, out_port):
        msg = of.ofp_packet_out()
        msg.data = packet
        action = of.ofp_action_output(port = out_port)
        msg.actions.append(action)
        self.connection.send(msg)

    def handle_arp(self, packet, in_port):
        """
        Controller Handles ARP packet
        """
        arp = packet.find("arp")
        if packet.payload.opcode == arp.REPLY: # Server or client reply
            log.debug("ARP request for entry proxy??");

            host = {
                'ip': arp.protosrc,
                'mac': arp.hwsrc,
                'port': in_port
            }
            if arp.protosrc in self.server_ips:
                log.debug("Server ARP reply :"+ str(arp.hwsrc));
                self.servers.append(host)
            else:
                log.debug("Client ARP reply :"+ str(arp.hwsrc));
                self.clients.append(host)

        elif packet.payload.opcode == arp.REQUEST: # Request for entry proxy
            log.debug("ARP request for "+str(arp.protodst)+" from " +str(arp.protosrc));

            packet = pkt.ethernet(
                    type = pkt.ethernet.ARP_TYPE,
                    src = self.mac,
                    dst = arp.hwsrc)
            packet.payload = pkt.arp(
                    opcode = pkt.arp.REPLY,
                    hwtype = pkt.arp.HW_TYPE_ETHERNET,
                    prototype = pkt.arp.PROTO_TYPE_IP,
                    hwsrc = self.mac,
                    hwdst = arp.hwsrc,
                    protosrc = self.ip,
                    protodst = arp.protosrc)
            msg = of.ofp_packet_out(
                    data = packet.pack(),
                    action = of.ofp_action_output(port = in_port))
            self.connection.send(msg)

    def new_connection(self, packet, in_port):
        src_mac = packet.src
        ip_packet = packet.find('ipv4')
        tcpp = packet.find('tcp')

        tcp_packet = pkt.tcp()
        tcp_packet.srcport = 11111
        tcp_packet.dstport = tcpp.srcport
        tcp_packet.seq = 0
        tcp_packet.ack = tcpp.seq + 1
        tcp_packet.off = 10
        tcp_packet.win = 29000
        tcp_packet.tcplen = tcpp.tcplen
        # tcp_packet.tcplen = pkt.tcp.MIN_LEN
        tcp_packet._setflag(tcp_packet.SYN_flag,1)
        tcp_packet._setflag(tcp_packet.ACK_flag,1)
        tcp_packet.options = tcpp.options
        # tcp_packet.payload = ""

        ipv4_packet = pkt.ipv4()
        ipv4_packet.iplen = pkt.ipv4.MIN_LEN + len(tcp_packet)
        ipv4_packet.protocol = pkt.ipv4.TCP_PROTOCOL
        ipv4_packet.dstip = ip_packet.srcip
        ipv4_packet.srcip = self.ip
        ipv4_packet.set_payload(tcp_packet)

        eth_packet = pkt.ethernet()
        eth_packet.set_payload(ipv4_packet)
        eth_packet.dst = src_mac
        eth_packet.src = self.mac
        eth_packet.type = pkt.ethernet.IP_TYPE

        self.send_packet(eth_packet, in_port)

    def push_message(self, packet, port):
        src_mac = packet.src
        ip_packet = packet.find('ipv4')
        tcpp = packet.find('tcp')

        tcp_packet = pkt.tcp()
        tcp_packet.srcport = 11111
        tcp_packet.dstport = tcpp.srcport
        tcp_packet.seq = tcpp.ack
        tcp_packet.ack = tcpp.seq + tcpp.tcplen - tcpp.off * 4
        tcp_packet.off = 5
        tcp_packet.tcplen = tcpp.tcplen
        tcp_packet.win = 29000
        tcp_packet._setflag(tcp_packet.SYN_flag,0)
        tcp_packet._setflag(tcp_packet.ACK_flag,1)
        tcp_packet.payload = tcpp.payload

        ipv4_packet = pkt.ipv4()
        ipv4_packet.iplen = pkt.ipv4.MIN_LEN + len(tcp_packet)
        ipv4_packet.protocol = pkt.ipv4.TCP_PROTOCOL
        ipv4_packet.dstip = ip_packet.srcip
        ipv4_packet.srcip = self.ip
        ipv4_packet.set_payload(tcp_packet)

        eth_packet = pkt.ethernet()
        eth_packet.set_payload(ipv4_packet)
        eth_packet.dst = src_mac
        eth_packet.src = self.mac
        eth_packet.type = pkt.ethernet.IP_TYPE

        self.send_packet(eth_packet, port)

    def _handle_PacketIn (self, event):
        """
        Handle packet in event
        """
        packet_in = event.ofp 
        packet = event.parsed
        src_mac = packet.src
        dst_mac = packet.dst
        in_port = event.port

        print "-- something in --"
        
        # handle arp messages
        if packet.type == pkt.ethernet.ARP_TYPE:
            self.handle_arp(packet, in_port)
            return
        if packet.type != pkt.ethernet.IP_TYPE:
            # self.resend_packet(packet_in, of.OFPP_FLOOD)
            return

        ip_packet = packet.find('ipv4')
        tcpp = packet.find('tcp')

        if ip_packet:
            log.debug("Receive "+ str(packet.type) + " from " 
                + str(ip_packet.srcip)+":"+ str(src_mac)
                + " to " + str(ip_packet.dstip)+":"+ str(dst_mac))
        else:
            log.debug("Receive "+ str(packet.type) + " from " + str(src_mac)
                        + " to " + str(dst_mac))


        if tcpp and ip_packet.dstip == self.ip:
            if tcpp and tcpp.SYN:
                print "Get a SYN!!!!"
                self.new_connection(packet, in_port)
                return

            if tcpp and tcpp.ACK:
                print "Get a ACK!!!! ack:"+str(tcpp.ack)+" len:"+str(tcpp.tcplen)
                self.push_message(packet, in_port)
                return
          # setup new connection




def launch (balancer_addr):
    balancer = IPAddr(balancer_addr)

    def start_switch (event):
        log.info("Controlling %s" % (event.connection))
        core.registerNew(Mixnet, event.connection, balancer)
    core.openflow.addListenerByName("ConnectionUp", start_switch)
