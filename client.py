import socket
import argparse
import sys
import threading

running = True

def connect(room_ip, room_port):
    print "client connecting to " + room_ip+":"+str(room_port)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # s.settimeout(2)
    s.connect((room_ip, room_port) )
    print "client connect to server"

    # background receive
    t = threading.Thread(target=receive, args = (s,))
    t.daemon = True
    t.start()
    # foreground send
    
    s.send('Someone joined the room'.encode())
    while running:
        send(s)
    
def receive(s):
    """
    Receive in background
    """
    while True:
        msg = s.recv(4096)
        if  msg :
            sys.stdout.write(msg)
            # sys.stdout.write('[Me] '); sys.stdout.flush() 
        else :
            print '\nDisconnected...\n'
            running = False
            sys.exit()

def send(s):
    """
    wait for stdin to send
    """
    msg = raw_input("\nEnter your message: ")
    s.send(msg.encode())
    # print "send"

def main(argv):
    if args.port:
        port = args.port
    else:
        port = 65530
    connect(args.ip, port)



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Stupid client for ')
    parser.add_argument('-i', '--ip', default='10.0.0.254', help='ip address of chatroom', required=True)
    parser.add_argument('-p', '--port', help='port of chatroom')
    args = parser.parse_args()
    main(sys.argv[1:])
