import socket, optparse
import threading
import sys


def handle_client(cs, address):
    while True:
        msg = cs.recv(512)

        if  msg :
            print str(msg.decode())
            # echo back
            cs.send(msg)
            f.write("%s: %s\n" % (str(address), msg))
            f.flush()
        else :
            print '\nClient leaves...\n'
            running = False
            sys.exit()

            
parser = optparse.OptionParser()
parser.add_option('-i', dest='ip', default='')
parser.add_option('-p', dest='port', type='int', default=65530)
(options, args) = parser.parse_args()

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind( (options.ip, options.port) )
s.listen(5)
print "server ready"

f = open('foo.txt','w')
while True:
    (cs, address) = s.accept()
    print "Receive connection from: " + str(address)
    msg = cs.recv(512)

    t = threading.Thread(target=handle_client, args = (cs,address))
    t.daemon = True
    t.start()

    # print str(msg.decode())
    # # echo back
    # cs.send(msg)
    # f.write("%s: %s\n" % (str(address), msg))
    # f.flush()




