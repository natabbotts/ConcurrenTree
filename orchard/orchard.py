#!/usr/bin/python

''' 
The general-purpose BCP user-level interface. This is the Python backend,
which communicates with the graphical client frontend in ./jsclient.

All peer communication and mutual hosting is handled by Python, which will
be capable of direct P2P communication and the high-level management of a
Kademlia DHT. Once that is in place, we can start building ECP support, and
start branching out to support more DHT algorithms.

'''

import optparse

defaults = {
	"1":{
		"peers":9090,
		"wsport":9091,
		"http":8080
	},
	"2":{
		"peers":9190,
		"wsport":9191,
		"http":8180
	},
	"3":{
		"peers":9290,
		"wsport":9291,
		"http":8280
	}

}

parser = optparse.OptionParser(description=''' 
Orchard is a BCP client with a web interface and
a Python server that runs in the background. It's
a reference implementation of the ConcurrenTree
concurrent text model.
''', version="Orchard v0.3")

parser.add_option("-p", "--peers", dest="peers", default=0,
	help="The port you want to host on for peers")
parser.add_option("-w", "--websocket", dest="wsport", default=0,
	help="The port you want to host for websocket clients")
parser.add_option("-H", "--http", dest="http", default=0,
	help="HTTP host port")
parser.add_option("-b", "--browserless", dest="browser", action="store_true",
	help="Open orchard with no browser")
parser.add_option("-v", action="store_true", help="Print version")
parser.add_option("-1", dest="portset", const="1", action="store_const", default="1",
	help="Use default port set")
parser.add_option("-2", dest="portset", const="2", action="store_const",
	help="Use secondary port set")
parser.add_option("-3", dest="portset", const="3", action="store_const",
	help="Use third port set")
args, startpeers = parser.parse_args()
parser.destroy()

#print args

parser.print_version()
if args.v:
	quit()

if args.portset:
	def default(argname):
		if getattr(args, argname)==0:
			setattr(args, argname, defaults[args.portset][argname])
	default("peers")
	default("wsport")
	default("http")

from ConcurrenTree.util.server.pool import *
from server import http, ws, peers, icon
from ConcurrenTree.util.storage import Storage

pool = pool.Pool()
docs = Storage()

# add interface servers
s_http = pool.start(http.HTTP, port=args.http)
s_ws   = pool.start(ws.WebSocketServer, port=args.wsport, docs=docs)
# Start browser
if not args.browser:
	s_http.open("/newclient#ws=" + str(s_ws.port))
# start notification icon
pool.start(icon.IconServer, pool)

# start background servers
peerserver = pool.start(peers.Peers, port=args.peers, docs = docs)

# Connect to cmdline peers
for peer in startpeers:
	peerserver.connect(peer)

try:
	pool.run()
except KeyboardInterrupt:
	print
	pool.close()
