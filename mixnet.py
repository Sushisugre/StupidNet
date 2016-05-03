from pox.core import core
import pox.openflow.libopenflow_01 as of
from pox.lib.addresses import IPAddr, EthAddr
from pox.lib.util import dpid_to_str
import pox.lib.packet as pkt

log = core.getLogger()
s1_dpid=0
s2_dpid=0
s3_dpid=0
s4_dpid=0
s5_dpid=0
# dpid:role
dpid_arr = [{}]

class Mixnet(object):
    """ Todo """
    def __init__ (self, connection, balancer_addr, server_ips):
        # Keep track of the connection to the switch     
        self.connection = connection
        # This binds our PacketIn event listener
        connection.addListeners(self)
        self.index = 0
        self.flow_map = {}
        self.mac = EthAddr("01:01:01:01:01:01")
        self.ip = IPAddr(balancer_addr)
        self.server_ips = server_ips
        self.servers = []
        self.clients = []

    def resend_packet (self, packet_in, out_port):
        """
        Instructs the switch to resend a packet      
        "packet_in" is the ofp_packet_in object the switch had 
        sent to the controller due to a table-miss.
        """
        msg = of.ofp_packet_out()
        msg.data = packet_in
        action = of.ofp_action_output(port = out_port)
        msg.actions.append(action)
        self.connection.send(msg)
        
    def _handle_PacketIn (self, event):
        """
        Handle packet in event
        """
        packet_in = event.ofp 
        packet = event.parsed
        src_mac = packet.src
        dst_mac = packet.dst
        in_port = event.port

        if packet.type != pkt.ethernet.IP_TYPE:
            self.resend_packet(packet_in, of.OFPP_FLOOD)
            return

        log.debug("Receive "+ str(packet.type) + " from " + str(src_mac))



"""
    Launch load balancer
    balancer: ip address of load balancer
    servers: ip address of servers
"""
def launch (balancer_addr, server_addrs):
    balancer = IPAddr(balancer_addr)
    server_ips = [IPAddr(x) for x in server_addrs.split(",")]

    def start_switch (event):
        log.info("Controlling %s" % (event.connection))
        log.info("Switch %s has come up.", dpid_to_str(event.dpid))
        core.registerNew(Mixnet, event.connection, balancer, server_ips)

    core.openflow.addListenerByName("ConnectionUp", start_switch)
