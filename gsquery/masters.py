from __init__ import *

class none(object):

	"""
	Master Server Class
	"""

	def __init__(self, host, port):
		try:
			self.host		= (socket.gethostbyname(host), int(port))
		except:
			pass

		self.socket		= socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		self.timeout	= 2

		self.filters	= {}

	def request(self, callback):
		self.socket.settimeout(self.timeout)

	def setfilter(self, name, value = None):
		self.filters[name] = value
	def removefilter(self, name):
		return self.filters.pop(name, None)

	def send(self, data):
		self.socket.sendto(data, self.host)
	def recv(self):
		try:
			return self.socket.recv(4096)
		except:
			return ""

class q2(none):

	"""
	Quake 2
	
	Filters
	----------------------------------------------------------------------------
	None
	"""

	REQUEST_SERVERS		= "query"

	def request(self, callback, *args, **kwargs):
		super(q2, self).request(callback, *args, **kwargs)
		
		self.send(self.REQUEST_SERVERS)
		servers = DataReader(self.recv())
		while servers.read("BBBB7sB") == (0xFF, 0xFF, 0xFF, 0xFF, "servers", 0x20):
			while servers.data:
				server = servers.read("BBBBH")
				callback(("%d.%d.%d.%d" % server[0:4], server[4]))
			servers.data = self.recv()


class q3(none):

	"""
	Quake 3
	
	Filters
	----------------------------------------------------------------------------
	protocol	Protocol Number
	empty		Include Empty Servers		(Broken?)
	full		Include Full Servers		(Broken?)
	"""

	REQUEST_SERVERS		= "\xFF\xFF\xFF\xFFgetservers %s %s"

	def request(self, callback, *args, **kwargs):
		super(q3, self).request(callback, *args, **kwargs)
		
		filters = self.filters.copy()
		
		self.send(self.REQUEST_SERVERS % (filters.pop("protocol", 0), " ".join(filters.keys())))
		servers = DataReader(self.recv())
		while servers.read("BBBB18sB") == (0xFF, 0xFF, 0xFF, 0xFF, "getserversResponse", 0x5C):
			while servers.data and not servers.data == "EOT":
				server = servers.read("BBBB") + servers.read("Hc", byteorder = "!")
				callback(("%d.%d.%d.%d" % server[0:4], server[4]))
			servers.data = self.recv()

class q4(none):

	"""
	Quake 4
	
	Filters
	----------------------------------------------------------------------------
	protocol	Protocol Number
	1			Unknown
				0x00
	2			Unknown
				0x00
	3			Unknown
				0x00
	"""

	REQUEST_SERVERS		= "\xFF\xFFgetServers\x00%c\x00\x01\x00\x00%c%c%c"

	def request(self, callback, *args, **kwargs):
		super(q4, self).request(callback, *args, **kwargs)
		
		filters = self.filters.copy()
		
		self.send(self.REQUEST_SERVERS % (filters.pop("protocol", 0), filters.pop(1, 0), filters.pop(2, 0), filters.pop(3, 0)))
		servers = DataReader(self.recv())
		while servers.read("BB7sB") == (0xFF, 0xFF, "servers", 0x00):
			while servers.data and not servers.data == "EOT":
				server = servers.read("BBBBH")
				callback(("%d.%d.%d.%d" % server[0:4], server[4]))
			servers.data = self.recv()

class hl2(none):

	"""
	Half-Life 2 / Source
	
	Filters
	----------------------------------------------------------------------------
	region		Region
				0x00 	US East coast
				0x01 	US West coast
				0x02 	South America
				0x03 	Europe
				0x04 	Asia
				0x05 	Australia
				0x06 	Middle East
				0x07 	Africa
				0xFF 	Rest of the world
	startip		Starting IP		(Broken?)
				a.b.c.d:port
	type		Server Type		(Broken?)
				d	Dedicated
				l	Listening
	secure		Servers Using Anti-Cheat Technology (VAC)
	gamedir		Servers Running The Specified Modification (ex. cstrike)
	map		Servers Running The Specified Map (ex. cs_italy)
	linux		Servers Running On A Linux Platform
	empty		Servers That Are Not Empty
	full		Servers That Are Not Full
	proxies		Servers That Are Spectator Proxies
	"""

	REQUEST_SERVERS		= "\x31%c%s\x00%s\x00"

	def request(self, callback, *args, **kwargs):
		super(hl2, self).request(callback, *args, **kwargs)
		
		filters = self.filters.copy()
		region = filters.pop("region", 0xFF)
		startip = filters.pop("startip", "0.0.0.0:0")
		others = "".join(["\\%s\\%s" % x for x in filters.items()])

		self.send(self.REQUEST_SERVERS % (region, startip, others))
		servers = DataReader(self.recv())
		while servers.read("BBBBBB") == (0xFF, 0xFF, 0xFF, 0xFF, 0x66, 0x0A):
			while servers.data:
				ip = servers.read("BBBB")
				port = servers.read("H", "!")[0]
				callback(("%d.%d.%d.%d" % ip, port))



