from pox.core import core
import pox.openflow.libopenflow_01 as of
from pox.lib.addresses import IPAddr, EthAddr
from pox.lib.util import dpid_to_str
import pox.lib.packet as pkt
import threading


log = core.getLogger()

class Chatroom(object):
    """ Controller as a chatroom """

    def __init__ (self, connection, room_ip):
        # Keep track of the connection to the switch     
        self.connection = connection
        # This binds our PacketIn event listener
        connection.addListeners(self)
        self.flow_map = {}
        self.mac = EthAddr("01:01:01:01:01:01")
        self.ip = IPAddr(room_ip)
        self.clients = {}

    def send_packet (self, packet, out_port):
        """
        Send a open flow packet out
        """
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
        """
        Send SYN/ACK to client, maintain connection info for new client
        """
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
        tcp_packet._setflag(tcp_packet.SYN_flag,1)
        tcp_packet._setflag(tcp_packet.ACK_flag,1)
        tcp_packet.options = tcpp.options

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

        client = {'ip':ip_packet.srcip, 'host_port':tcpp.srcport, 
                    'switch_port':in_port, 'mac':src_mac, 'seq':1, 'ack':1}
        key = str(ip_packet.srcip)+":"+str(tcpp.srcport)
        self.clients[key] = client
        self.send_packet(eth_packet, in_port)

    def push_message(self, packet, port):
        """
        Push message from one client to all connected clients
        """
        for key, client in self.clients.iteritems():
            eth_packet = self.pack_message(packet, client)
            self.send_packet(eth_packet, client['switch_port'])

        print "pushed message to clients"

    def send_control_packet(self, packet, port, SYN, ACK, FIN):
        """
        Send control packet SYN, ACK, FIN according to specified flag
        """
        src_mac = packet.src
        ip_packet = packet.find('ipv4')
        tcpp = packet.find('tcp')

        key = str(ip_packet.srcip)+":"+str(tcpp.srcport)
        client = self.clients[key]
        conn_seq = client['seq']

        if tcpp.FIN:
            client['ack'] = client['ack'] + 1
        else:
            client['ack'] = tcpp.seq + tcpp.tcplen - tcpp.off * 4

        tcp_packet = pkt.tcp()
        tcp_packet.srcport = 11111
        tcp_packet.dstport = tcpp.srcport
        tcp_packet.seq = conn_seq
        tcp_packet.ack = client['ack']
        tcp_packet.off = 5
        tcp_packet.tcplen = pkt.tcp.MIN_LEN
        tcp_packet.win = 29000
        tcp_packet._setflag(tcp_packet.SYN_flag, SYN)
        tcp_packet._setflag(tcp_packet.ACK_flag, ACK)
        tcp_packet._setflag(tcp_packet.FIN_flag, FIN)

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


    def pack_message(self, packet, client):
        """
        Repack a message packet according to different clients connection info
        """
        ip_packet = packet.find('ipv4')
        tcpp = packet.find('tcp')

        client_ip = client['ip']
        client_mac = client['mac']
        client_port = client['host_port']
        conn_seq = client['seq']
        conn_ack = client['ack']

        tcp_packet = pkt.tcp()
        tcp_packet.srcport = 11111
        tcp_packet.dstport = client_port
        tcp_packet.seq = conn_seq
        tcp_packet.ack = conn_ack
        tcp_packet.off = 5
        tcp_packet.tcplen = tcpp.tcplen
        tcp_packet.win = 29000
        tcp_packet._setflag(tcp_packet.SYN_flag,0)
        tcp_packet._setflag(tcp_packet.ACK_flag,1)
        tcp_packet._setflag(tcp_packet.PSH_flag,1)
        tcp_packet.payload = tcpp.payload

        ipv4_packet = pkt.ipv4()
        ipv4_packet.iplen = pkt.ipv4.MIN_LEN + len(tcp_packet)
        ipv4_packet.protocol = pkt.ipv4.TCP_PROTOCOL
        ipv4_packet.dstip = client_ip
        ipv4_packet.srcip = self.ip
        ipv4_packet.set_payload(tcp_packet)

        eth_packet = pkt.ethernet()
        eth_packet.set_payload(ipv4_packet)
        eth_packet.dst = client_mac
        eth_packet.src = self.mac
        eth_packet.type = pkt.ethernet.IP_TYPE

        return eth_packet

    def update_seq(self, packet):
        """
        After receiving ACK from the client
        Update the next packet sequence number for it
        """
        ip_packet = packet.find('ipv4')
        tcpp = packet.find('tcp')
        client = self.get_client(packet)
        if client:
            client['seq'] = tcpp.ack

    def remove_client():
        """
        Remove a client after connection close
        """
        ip_packet = packet.find('ipv4')
        tcpp = packet.find('tcp')
        key = str(ip_packet.srcip)+":"+str(tcpp.srcport)
        del self.clients[key]

    def get_client(self, packet):
        """
        Get connected client by its socket identifier (ip:port)
        """
        ip_packet = packet.find('ipv4')
        tcpp = packet.find('tcp')
        key = str(ip_packet.srcip)+":"+str(tcpp.srcport)
        client = self.clients[key]
        return client

    def _handle_PacketIn (self, event):
        """
        Handle packet_in event
        """
        packet_in = event.ofp 
        packet = event.parsed
        src_mac = packet.src
        dst_mac = packet.dst
        in_port = event.port
        
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
            if tcpp and tcpp.FIN:
                print "Get a FIN!!!!"
                # close connection
                self.send_control_packet(packet, in_port, False, True, False)
                self.send_control_packet(packet, in_port, False, True, True)

            if tcpp and tcpp.ACK:
                data_len = tcpp.tcplen - tcpp.off * 4
                if data_len != 0:
                    # a data packet
                    # send ACK
                    self.send_control_packet(packet, in_port, False, True, False)
                    self.push_message(packet, in_port)
                else:
                    # an ack
                    self.update_seq(packet)
                return



def launch (room_ip):
    balancer = IPAddr(room_ip)

    def start_switch (event):
        log.info("Controlling %s" % (event.connection))
        core.registerNew(Chatroom, event.connection, balancer)
    core.openflow.addListenerByName("ConnectionUp", start_switch)
