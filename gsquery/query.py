from __init__ import *
import random, select

class Batch:

	def __init__(self, socketcount = 4, timeout = 4, maxcurrent = 8):
		self.servers	= []
		self.sockets	= [socket.socket(socket.AF_INET, socket.SOCK_DGRAM) for x in range(socketcount)]

		self.timeout	= timeout
		self.maxcurrent	= maxcurrent
		
		for x in self.sockets:
			x.setblocking(0)

	def addserver(self, server):
		self.servers.append(server)

	def queryall(self, querytype, callback):
		queued		= self.servers[:]
		servers		= {}

		while queued or servers:
			while len(servers) <= self.maxcurrent and queued:
				server = queued.pop(0)
				server.request(querytype)
				if not server.complete():
					servers[server.host] = server
					while server.outbound:
						random.choice(self.sockets).sendto(server.outbound.pop(0), server.host)
				else:
					callback(server)
					
			if not servers: break
			(readers, writers, errors) = select.select(self.sockets, [], [], self.timeout)

			for reader in readers:
				while True:
					try:
						packet = reader.recvfrom(4096)
						if servers.has_key(packet[1]):
							server = servers[packet[1]]
							server.parsepackets(packet[0])
							while server.outbound:
								random.choice(self.sockets).sendto(server.outbound.pop(0), server.host)
						else:
							print "Crap Packet", packet[1], packet[0]
							pass
					except socket.error, z:
						break
			for server in servers.values():
				if not readers:
					print "Dead", server.host, server.required, server.packets, server.packetids
					del servers[server.host]
				elif server.complete():
					callback(servers.pop(server.host))
					
