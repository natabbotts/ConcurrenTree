from threading import Lock, Thread, Event
from Queue import Queue, Empty
import traceback

import connection

class Pool:
	''' A collection of server objects that provide real
	or virtual peers. '''

	def __init__(self):
		self.servers = []
		self.lock = Lock()
		self.inputevent = Event()
		self.closed = False
		self._close_signal = False
		self.env = [[],[]]

		self.uniquelock = Lock()
		self.unique = {}

	def start(self, cls, *args, **kwargs):
		''' Add a server to the pool '''
		try:
			server = cls(*args, **kwargs)
			server.cycleflag = self.cycleflag
			thread = Thread(target=server.run)
			thread.start()
			with self.lock:
				self.check_closed()
				self.servers.append((server, thread, []))
				return server
		except Exception as e:
			self.crash(e)
			quit(1)

	def run(self):
		''' Run the pool, allowing interserver communication '''
		while not self.closed:
			#print "cycling"
			self.buffer_flip()
			if not self.buffer:
				# wait for new inputs
				self.inputevent.wait(timeout=1)
				self.inputevent.clear()
			with self.lock:
				s = 0
				while s < len(self.servers):
					if self.server(s).closed:
						del self.servers[s]
					else:
						try:
							self.process_server(s)
						except Exception as e:
							self.crash(e)
						s += 1
			if self._close_signal:
				self.close()

	def run_threaded(self):
		t = Thread(target=self.run)
		t.start()
		return t

	def process_server(self, i):
		policy = self.server(i).policy()
		# Accept new connections
		for conn in self.server(i).starting():
			self.connect(i, conn)
		def broadcast(msg):
			print "Appending message to buffer"
			self.inputevent.set()
			self.buffer.append(msg)
		# Scan through connections
		c = 0
		while c < len(self.connections(i)):
			try:
				conn = self.connections(i)[c]
				for msg in self.lastbuffer:
					print "Exporting from lastbuffer: ",msg
					policy.output(msg, conn, broadcast)
				# Do something with the input, according to policy
				while True:
					try:
						msg = conn.queue.server_pull(0)
						print "Pool receiving message:  ", i, c, msg
						policy.input(msg, conn, broadcast)
					except Empty:
						break
				conn.cycle()
				if conn.closed:
					del self.servers[i][2][c]
				else:
					c += 1
			except Exception as e:
				self.crash(e)

	def cycleflag(self):
		#print "cycleflag"
		self.inputevent.set()

	def connect(self, server, conn):
		print "New connection:",server
		if not isinstance(conn, connection.Connection):
			raise TypeError("Server %s passing connection objects that are not subclasses of Connection" % repr(server))
		conn.queue.server_notify(self.cycleflag) # Set pool notification callback
		conn.queue.client_notify(self.cycleflag) # Set pool notification callback
		conn.cycleflag = self.cycleflag
		conn.getunique = self.getunique
		self.servers[server][2].append(conn)

	def server(self, index):
		return self.servers[index][0]

	def thread(self, index):
		return self.servers[index][1]

	def connections(self, index):
		return self.servers[index][2]

	@property
	def buffer(self):
		''' The part of the environment currently being edited '''
		return self.env[0]

	@property
	def lastbuffer(self):
		''' The read-only results of the last env cycle '''
		return self.env[1]

	def buffer_flip(self):
		self.env = [[], self.buffer]

	def properties(self):
		with self.lock:
			result = {}
			for i in range(len(self.servers)):
				props = self.server(i).properties
				basename = ""
				try:
					basename = props['name']
				except KeyError:
					basename = str(props.__class__)
				name = basename
				number = 0
				while name in result:
					number += 1
					name = basename+str(number)
				result[name] = props
			return result

	def crash(self, e):
		''' 
			Process an error in a way that will not
			bork the thread. 

			Warning: it will stop any error except
			KeyboardInterrupt and never raise it,
			therefore any code after the except
			statement that calls self.crash(e)
			will run whether an error occurs or not.
			This is normal behavior for except
			statements, I'm just remindin' ya.
		'''
		traceback.print_exc()
		if type(e)==KeyboardInterrupt:
			self.close()

	def close(self):
		with self.lock:
			self.check_closed()
			self.closed = True
			for i in self.servers:
				i[0].close()
			for i in self.servers:
				i[1].join()

	def close_signal(self):
		''' Close pool in a thread-safe way from a server thread '''
		self._close_signal = True

	def check_closed(self):
		if self.closed:
			raise ClosedError("Pool is closed")

	def getunique(self, key):
		with self.uniquelock:
			if not key in self.unique:
				self.unique[key] = 0
			self.unique[key] += 1
			return self.unique[key]
