from mininet.topo import Topo

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

topos = { 'mixtopo': ( lambda: MixTopo() ) }
