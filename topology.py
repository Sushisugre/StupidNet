 
from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import CPULimitedHost
from mininet.link import TCLink
from mininet.util import dumpNodeConnections
from mininet.log import setLogLevel
from mininet.node import Controller 
from mininet.cli import CLI
from functools import partial
from mininet.node import RemoteController
import os

class MixTopo(Topo):
    """a simple topo for testing"""
    def __init__(self):
        Topo.__init__( self )

        # Add hosts and switches
        h1 = self.addHost( 'h1' )
        h2 = self.addHost( 'h2' )
        h3 = self.addHost( 'h3' )
        h4 = self.addHost( 'h4' )
        s1 = self.addSwitch( 's1' )
        s2 = self.addSwitch( 's2' )
        # Add links
        self.addLink( h1, s1 )
        self.addLink( h2, s1 )
        self.addLink( h3, s1 )
        self.addLink( s1, s2 )
        self.addLink( s2, h4 ) 
  

def setup():
    topo = MixTopo()
    #net = Mininet(topo=topo, host=CPULimitedHost, link=TCLink, controller=POXcontroller1)
    net = Mininet(topo=topo, host=CPULimitedHost, link=TCLink, controller=partial(RemoteController, ip='127.0.0.1', port=6633))
    net.start()
    print "Dumping host connections"
    dumpNodeConnections(net.hosts)
    s1,s2 = net.get('s1','s2')
    h1,h2,h3,h4=net.get('h1','h2','h3','h4')
    h1.setMAC("0:0:0:0:1:0")
    h2.setMAC("0:0:0:0:2:0")
    h3.setMAC("0:0:0:0:3:0")
    h4.setMAC("0:0:0:0:4:0")

    result1=s2.cmd('ifconfig')
    print result1

    result1=h4.cmd('ifconfig')
    print result1

    CLI(net)
    net.stop()
 
if __name__ == '__main__':
    setLogLevel('info')
    setup()
