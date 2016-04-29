from pox.core import core
import pox.openflow.libopenflow_01 as of
from pox.lib.addresses import IPAddr, EthAddr
import pox.lib.packet as pkt

log = core.getLogger()

class Mixnet(object):
    """ Todo """



"""
    Launch load balancer
    balancer: ip address of load balancer
    servers: ip address of servers
"""
def launch (balancer_addr, server_addrs):
    balancer = Mixnet(balancer_addr)
    # server_ips = [IPAddr(x) for x in server_addrs.split(",")]

    def start_switch (event):
        log.debug("Controlling %s" % (event.connection))
        core.registerNew(Load_Balancer,event.connection, balancer, server_ips)

    core.openflow.addListenerByName("ConnectionUp", start_switch)
