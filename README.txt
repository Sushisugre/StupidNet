README

# Put source file under pox/ folder

# Start controller
./pox.py log.level --DEBUG mixnet --room_ip=10.0.0.254

# Start a topology
sudo mn --topo single,10 --mac --arp --switch ovsk --controller remote

# Open xterm window for a few hosts
xterm h1 h2 h3 h4

# In h1's terminal connect to chatroom
python client.py -i 10.0.0.254

# In h12s terminal connect to chatroom
python client.py -i 10.0.0.254 -n DeadPool
