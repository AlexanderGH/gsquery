from __init__ import *

INFO_NONE		= 0
INFO_CHALLENGE	= 1
INFO_STATUS		= 2
INFO_PLAYER		= 4
INFO_RULES		= 8
INFO_TEAM		= 16
INFO_ALL		= INFO_CHALLENGE | INFO_STATUS | INFO_PLAYER | INFO_RULES | INFO_TEAM

class none(object):
	SUPPORTS = INFO_NONE

	def __init__(self, host, port):
		try:
			self.host	= (socket.gethostbyname(host), int(port))
		except:
			pass

		self.packets	= []
		self.packetids	= {}
		self.outbound	= []
		self.required	= INFO_NONE
		
		self.data		= {}

	def requires(self, infotype = INFO_ALL): return self.required & infotype
	def require(self, infotype): self.required = (self.required | infotype) & self.SUPPORTS
	def unrequire(self, infotype): self.required = self.required ^ (self.required & infotype)
	def complete(self): return ( self.requires() == INFO_NONE ) and ( len(self.packetids) == 0 ) and ( len(self.outbound) == 0 )

	def request(self, infotype = INFO_NONE):
		self.require(infotype)

	def parsepackets(self, packet = None):
		if not packet is None:
			self.packets.append(packet)

	def __getitem__(self, key):
		if not self.data.has_key(key): self.query(key)
		return self.data.get(key, None)

	def query(self, infotype, timeout = 2):
		connection = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		connection.settimeout(timeout)
		try: connection.connect(self.host)
		except: return
		self.request(infotype)
		while not self.complete():
			try:
				while self.outbound:
					connection.send(self.outbound.pop(0))
				self.parsepackets(connection.recv(4096))
			except:
				break
		connection.close()

	def _findpacket(self, header):
		size = len(header)
		for index, packet in enumerate(self.packets):
			if packet[0:size] == header:
				return index

class hl(none):

	"""
	Half-Life
	"""

	SUPPORTS = INFO_STATUS | INFO_PLAYER | INFO_RULES

	OLD_INFO						= "\xFF\xFF\xFF\xFFdetails"
	OLD_PLAYER						= "\xFF\xFF\xFF\xFFplayers"
	OLD_RULES						= "\xFF\xFF\xFF\xFFrules"

	A2S_INFO						= "\xFF\xFF\xFF\xFF\x54Source Engine Query\x00"
	A2S_PLAYER						= "\xFF\xFF\xFF\xFF\x55"
	A2S_RULES						= "\xFF\xFF\xFF\xFF\x56"
	A2S_SERVERQUERY_GETCHALLENGE	= "\xFF\xFF\xFF\xFF\x57"

	S2A_INFO						= "\x6D"
	S2A_PLAYER						= "\x44"
	S2A_RULES						= "\x45"
	S2C_CHALLENGE					= "\x41"

	def request(self, infotype, *args, **kwargs):
		super(hl, self).request(infotype, *args, **kwargs)
		if self.requires(INFO_STATUS):
			if self.data.has_key(INFO_CHALLENGE): self.outbound.append(self.A2S_INFO)
			else: self.outbound.append(self.OLD_INFO)
		if self.requires(INFO_PLAYER):
			if self.data.has_key(INFO_CHALLENGE): self.outbound.append(self.A2S_PLAYER + self.data[INFO_CHALLENGE])
			else: self.outbound.append(self.OLD_PLAYER)
		if self.requires(INFO_RULES):
			if self.data.has_key(INFO_CHALLENGE): self.outbound.append(self.A2S_RULES + self.data[INFO_CHALLENGE])
			else: self.outbound.append(self.OLD_RULES)
		if self.requires() and not self.data.has_key(INFO_CHALLENGE):
			self.outbound.append(self.A2S_SERVERQUERY_GETCHALLENGE)

	def parsepackets(self, packet, *args, **kwargs):
		super(hl, self).parsepackets(packet, *args, **kwargs)
		for packet in self.packets:
			self.packets.remove(packet)
			if packet[0:4] == "\xFE\xFF\xFF\xFF":
				packetid = packet[4:8]
				if not self.packetids.has_key(packetid):
					self.packetids[packetid] = [1, ord(packet[8]) & 0x0F]
				if ord(packet[8]) - 0x10 >= 0:
					previouspacket = self._findpacket(packet[0:8] + chr(ord(packet[8]) - 0x10))
					if previouspacket is None:
						self.packets.append(packet)
					else:
						self.packets[previouspacket] += packet[9:]
						self.packetids[packetid][0] += 1
						if self.packetids[packetid][0] == self.packetids[packetid][1]:
							del self.packetids[packetid]
							self.parsepackets(self.packets.pop(previouspacket)[9:])
				else:
					self.packets.insert(0, packet)
			elif packet[0:4] == "\xFF\xFF\xFF\xFF":
				if packet[4] == self.S2C_CHALLENGE:
					self.data[INFO_CHALLENGE] = packet[5:9]
					self.request(self.requires())
				elif packet[4] == self.S2A_INFO:
					self.data[INFO_STATUS] = self.__parseinfo(packet[5:])
					self.unrequire(INFO_STATUS)
				elif packet[4] == self.S2A_PLAYER:
					self.data[INFO_PLAYER] = self.__parseplayer(packet[5:])
					self.unrequire(INFO_PLAYER)
				elif packet[4] == self.S2A_RULES:
					self.data[INFO_RULES] = self.__parserules(packet[5:])
					self.unrequire(INFO_RULES)
	
	def __parseinfo(self, data):
		information = {}
		variables = DataReader(data)
		(
			information["gameip"],
			information["hostname"],
			information["mapname"],
			information["gametype"],
			information["gamedescription"],
			information["numplayers"],
			information["maxplayers"],
			information["networkversion"],
			information["dedicated"],
			information["os"],
			information["password"],
			information["mod"]
		) = variables.readto(0x00, 5) + variables.read("BBBBBBB")
		if information["mod"]:
			(
				information["mod_website"],
				information["mod_download"],
				information["mod_unused"],
				information["mod_version"],
				information["mod_size"],
				information["mod_serveronly"],
				information["mod_clientdll"]
			) = variables.readto(0x00, 3) + variables.read('llBB')
		(information["secure"], information["bots"]) = variables.read("BB")
		return information
	
	def __parseplayer(self, data):
		information = []
		players = DataReader(data)
		playercount = players.read("B")[0]
		while len(players.read("B")):
			information.append(
				{
				"playername":	players.readto(0x00, 1)[0],
				"kills":		players.read("l")[0],
				"connected":	int(players.read("f")[0])
				}
			)
		return information

	def __parserules(self, data):
		information = {}
		rules = DataReader(data)
		rulecount = rules.read("h")[0]
		for x in xrange(rulecount):
			(name, value) = rules.readto(0x00, 2)
			information[name] = value 
		return information

class hl2(none):

	"""
	Half-Life 2
	"""

	SUPPORTS = INFO_CHALLENGE | INFO_STATUS | INFO_PLAYER | INFO_RULES

	A2S_INFO						= "\xFF\xFF\xFF\xFF\x54Source Engine Query\x00"
	A2S_PLAYER						= "\xFF\xFF\xFF\xFF\x55"
	A2S_RULES						= "\xFF\xFF\xFF\xFF\x56"
	A2S_SERVERQUERY_GETCHALLENGE	= "\xFF\xFF\xFF\xFF\x57"
	
	S2A_INFO						= "\x49"
	S2A_PLAYER						= "\x44"
	S2A_RULES						= "\x45"
	S2C_CHALLENGE					= "\x41"

	def request(self, infotype, *args, **kwargs):
		super(hl2, self).request(infotype, *args, **kwargs)
		if self.requires(INFO_STATUS):
			self.outbound.append(self.A2S_INFO)
		if self.requires(INFO_PLAYER) and self.data.has_key(INFO_CHALLENGE):
			self.outbound.append(self.A2S_PLAYER + self.data[INFO_CHALLENGE])
		if self.requires(INFO_RULES) and self.data.has_key(INFO_CHALLENGE):
			self.outbound.append(self.A2S_RULES + self.data[INFO_CHALLENGE])
		if self.requires(INFO_CHALLENGE) or (self.requires(INFO_PLAYER | INFO_RULES) and not self.data.has_key(INFO_CHALLENGE)):
			self.outbound.append(self.A2S_SERVERQUERY_GETCHALLENGE)

	def parsepackets(self, packet, *args, **kwargs):
		super(hl2, self).parsepackets(packet, *args, **kwargs)
		for packet in self.packets:
			self.packets.remove(packet)
			if packet[0:4] == "\xFE\xFF\xFF\xFF":
				packetid = packet[4:8]
				if self.packetids.has_key(packetid):
					self.packetids[packetid][1] += 1
					packet = "\xFF\xFF\xFF\xFF" + self.packetids[packetid][0] + packet[9:]
					if self.packetids[packetid][1] == self.packetids[packetid][2]:
						del self.packetids[packetid]
				else:
					self.packetids[packetid] = [packet[13], 1, ord(packet[8]) & 0x0F]
					self.packets.append(packet[9:])
			elif packet[0:4] == "\xFF\xFF\xFF\xFF":
				if packet[4] == self.S2C_CHALLENGE:
					self.data[INFO_CHALLENGE] = packet[5:9]
					self.unrequire(INFO_CHALLENGE)
					if self.requires(INFO_PLAYER | INFO_RULES):
						self.request(INFO_NONE)
				elif packet[4] == self.S2A_INFO:
					self.data[INFO_STATUS] = self.__parseinfo(packet[5:])
					self.unrequire(INFO_STATUS)
				elif packet[4] == self.S2A_PLAYER:
					self.data[INFO_PLAYER] = self.__parseplayer(packet[5:])
					self.unrequire(INFO_PLAYER)
				elif packet[4] == self.S2A_RULES:
					self.data[INFO_RULES] = self.__parserules(packet[5:])
					self.unrequire(INFO_RULES)
	
	def __parseinfo(self, data):
		information = {}
		variables = DataReader(data)
		(
			information["networkversion"],
			information["hostname"],
			information["mapname"],
			information["gametype"],
			information["gamedescription"],
			information["appid"],
			information["numplayers"],
			information["maxplayers"],
			information["numbots"],
			information["dedicated"],
			information["os"],
			information["password"],
			information["secure"],
			information["gameversion"]
		) = variables.read("B") + variables.readto(0x00, 4) + variables.read("hBBBBBBB") + variables.readto(0x00, 1)
		return information
	
	def __parseplayer(self, data):
		information = []
		players = DataReader(data)
		count = players.read("B")[0]
		while len(players.read("B")):
			information.append(
				{
				"playername":	players.readto(0x00, 1)[0],
				"kills":		players.read("l")[0],
				"connected":	int(players.read("f")[0])
				}
			)
		return information
	def __parserules(self, data):
		information = {}
		rules = DataReader(data)
		rulecount = rules.read("h")[0]
		for x in xrange(rulecount):
			(name, value) = rules.readto(0x00, 2)
			information[name] = value
		return information

class gs(none):

	"""
	GameSpy
	"""

	SUPPORTS = INFO_STATUS | INFO_PLAYER | INFO_RULES | INFO_TEAM

	REQUEST_INFO		= "\\echo\\[info]\\basic\\\\info\\"
	REQUEST_PLAYER		= "\\echo\\[players]\\players\\"
	REQUEST_RULES		= "\\echo\\[rules]\\rules\\"

	def request(self, infotype, *args, **kwargs):
		super(gs, self).request(infotype, *args, **kwargs)
		if self.requires(INFO_STATUS):
			self.data[INFO_STATUS] = {}
			self.outbound.append(self.REQUEST_INFO)
		if self.requires(INFO_PLAYER | INFO_TEAM):
			self.data[INFO_PLAYER] = []
			self.data[INFO_TEAM] = []
			self.outbound.append(self.REQUEST_PLAYER)
		if self.requires(INFO_RULES):
			self.data[INFO_RULES] = {}
			self.outbound.append(self.REQUEST_RULES)

	def parsepackets(self, packet, *args, **kwargs):
		super(gs, self).parsepackets(packet, *args, **kwargs)
		for packet in self.packets:
			self.packets.remove(packet)
			pairs = packet.split("\\")[1:]
			if len(pairs) == 2: break
			queryid = pairs[pairs[::2].index("queryid") * 2 + 1].split(".")
			if not self.packetids.has_key(queryid[0]):
				self.packetids[queryid[0]] = [0, None]
			if pairs[::2].count("final"):
				self.packetids[queryid[0]][1] = int(queryid[1])
			self.packetids[queryid[0]][0] += 1
			if self.packetids[queryid[0]][0] == self.packetids[queryid[0]][1]:
				del self.packetids[queryid[0]]
			while len(pairs):
				key = pairs.pop(0)
				keyparts = key.split("_")
				if key in ("queryid", "final", "echoresponse"):
					value = pairs.pop(0)
					if value == "[info]": self.unrequire(INFO_STATUS)
					elif value == "[players]": self.unrequire(INFO_PLAYER | INFO_TEAM)
					elif value == "[rules]": self.unrequire(INFO_RULES)
				elif len(keyparts) == 2 and keyparts[1].isdigit():
					if keyparts[0] == "teamname":
						self.data[INFO_TEAM] += [{}] * (1 + int(keyparts[1]) - len(self.data[INFO_TEAM]))
						self.data[INFO_TEAM][int(keyparts[1])][keyparts[0]] = pairs.pop(0)
					else:
						self.data[INFO_PLAYER] += [{}] * (1 + int(keyparts[1]) - len(self.data[INFO_PLAYER]))
						self.data[INFO_PLAYER][int(keyparts[1])][keyparts[0]] = pairs.pop(0)
				else:
					value = pairs.pop(0)
					if self.data.has_key(INFO_STATUS): self.data[INFO_STATUS][key] = value
					if self.data.has_key(INFO_RULES): self.data[INFO_RULES][key] = value

class gs2(none):

	"""
	GameSpy 2
	"""

	SUPPORTS = INFO_STATUS | INFO_PLAYER | INFO_TEAM

	REQUEST_INFO		= "\xFE\xFD\x00\x00\x00\x00\x01\xFF\x00\x00"
	REQUEST_PLAYER		= "\xFE\xFD\x00\x00\x00\x00\x02\x00\xFF\x00"
	REQUEST_TEAM		= "\xFE\xFD\x00\x00\x00\x00\x03\x00\x00\xFF"

	def request(self, infotype, *args, **kwargs):
		super(gs2, self).request(infotype, *args, **kwargs)
		if self.requires(INFO_STATUS):
			self.outbound.append(self.REQUEST_INFO)
		if self.requires(INFO_PLAYER):
			self.outbound.append(self.REQUEST_PLAYER)
		if self.requires(INFO_TEAM):
			self.outbound.append(self.REQUEST_TEAM)

	def parsepackets(self, packet, *args, **kwargs):
		super(gs2, self).parsepackets(packet, *args, **kwargs)
		for packet in self.packets:
			self.packets.remove(packet)
			if packet[0:4] == "\x00\x00\x00\x00":
				if packet[4] == self.REQUEST_INFO[6]:
					self.data[INFO_STATUS] = self.__parseinfo(packet[5:])
					self.unrequire(INFO_STATUS)
				if packet[4] == self.REQUEST_PLAYER[6]:
					self.data[INFO_PLAYER] = self.__parseplayer(packet[5:])
					self.unrequire(INFO_PLAYER)
				if packet[4] == self.REQUEST_TEAM[6]:
					self.data[INFO_TEAM] = self.__parseplayer(packet[5:])
					self.unrequire(INFO_TEAM)

	def __parseinfo(self, data):
		information = {}
		variables = DataReader(data)
		while variables.data:
			(name, value) = variables.readto(0x00, 2)
			if name: information[name] = value
		return information
		
	def __parseplayer(self, data):
		information = []
		players = DataReader(data)
		if players.read("B"):
			count = players.read("B")[0]
			labels = []
			while players.data:
				label = players.readto(0x00).split("_")
				if not label[0]: break
				labels.append(label[0])
			while players.data:
				player = {}
				for x in labels:
					value = players.readto(0x00)
					if not value == "": player[x] = value
				if player: information.append(player)
		return information

class gs3(none):

	"""
	GameSpy 3
	"""

	SUPPORTS = INFO_CHALLENGE | INFO_STATUS | INFO_PLAYER | INFO_TEAM

	REQUEST_ALL	= "\xFE\xFD\x00\x00\x00\x00\x00\xFF\xFF\xFF\x01"
	REQUEST_CHALLENGE	= "\xFE\xFD\x09\x00\x00\x00\x00"
	REQUEST_ALL_CHALLENGE	= "\xFE\xFD\x00\x00\x00\x00\x00%s\xFF\xFF\xFF\x01"

	def request(self, infotype, *args, **kwargs):
		super(gs3, self).request(infotype, *args, **kwargs)
		if self.data.has_key(INFO_CHALLENGE):
			self.data[INFO_STATUS] = {}
			self.data[INFO_PLAYER] = []
			self.data[INFO_TEAM] = []
			self.outbound.append(self.REQUEST_ALL_CHALLENGE % self.data[INFO_CHALLENGE]);
		elif self.requires(INFO_STATUS | INFO_PLAYER | INFO_TEAM):
			self.data[INFO_STATUS] = {}
			self.data[INFO_PLAYER] = []
			self.data[INFO_TEAM] = []
			self.outbound.append(self.REQUEST_CHALLENGE)
			self.outbound.append(self.REQUEST_ALL)

	def parsepackets(self, packet, *args, **kwargs):
		super(gs3, self).parsepackets(packet, *args, **kwargs)
		for packet in self.packets:
			self.packets.remove(packet)
			if packet[0:5] == "\x09\x00\x00\x00\x00":
				code = int(packet[5:-1])
				self.data[INFO_CHALLENGE] = chr((code >> 24) & 255)+chr((code >> 16) & 255)+chr((code >> 8) & 255)+chr(code & 255);
				self.unrequire(INFO_CHALLENGE)
				self.outbound = []
				self.request(self.requires())
			elif packet[0:14] == "\x00\x00\x00\x00\x00splitnum\x00":
				if not self.data.has_key(INFO_CHALLENGE):
					self.data[INFO_CHALLENGE] = ""
					self.unrequire(INFO_CHALLENGE)
				if not self.packetids.has_key(""):
					self.packetids[""] = [0, None]
				if ord(packet[14]) >= 0x7F:
					self.packetids[""][1] = ord(packet[14]) - 0x7F
				self.packetids[""][0] += 1
				if self.packetids[""][0] == self.packetids[""][1]:
					del self.packetids[""]
				table = ord(packet[15])
				packetbody = DataReader(packet[16:])
				while table == 0 and packetbody.data:
					key = packetbody.readto(0x00)
					if not key: table = packetbody.read("B")[0]
					else: self.data[INFO_STATUS][key] = packetbody.readto(0x00)
					self.unrequire(INFO_STATUS)
				while table == 1 and packetbody.data:
					column = packetbody.readto(0x00)
					if column == "":
						table = packetbody.read("B")
						if table: table = table[0]
					elif column.endswith("_"):
						row = packetbody.read("B")[0]
						while packetbody.data:
							value = packetbody.readto(0x00)
							if not value: break
							self.data[INFO_PLAYER] += [{}] * (1 + row - len(self.data[INFO_PLAYER]))
							self.data[INFO_PLAYER][row][column.rstrip("_")] = value
							row += 1
					self.unrequire(INFO_PLAYER)
				while table == 2:
					column = packetbody.readto(0x00)
					if not column:
						table = packetbody.read("B")
						if table: table = table[0]
					else:
						row = packetbody.read("B")[0]
						while packetbody.data:
							value = packetbody.readto(0x00)
							if not value: break
							self.data[INFO_TEAM] += [{}] * (1 + row - len(self.data[INFO_TEAM]))
							self.data[INFO_TEAM][row][column] = value
							row += 1
					self.unrequire(INFO_TEAM)

class q3(none):

	"""
	Quake 3
	"""

	SUPPORTS = INFO_STATUS | INFO_PLAYER

	REQUEST_INFO		= "\xFF\xFF\xFF\xFFgetinfo"
	REQUEST_PLAYER		= "\xFF\xFF\xFF\xFFgetstatus"

	def request(self, infotype, *args, **kwargs):
		super(q3, self).request(infotype, *args, **kwargs)
		if self.requires(INFO_STATUS):
			self.outbound.append(self.REQUEST_INFO)
		if self.requires(INFO_PLAYER):
			self.outbound.append(self.REQUEST_PLAYER)

	def parsepackets(self, packet, *args, **kwargs):
		super(q3, self).parsepackets(packet, *args, **kwargs)
		for packet in self.packets:
			self.packets.remove(packet)
			packetsegments = packet.split("\n")
			if packetsegments[0][0:4] == "\xFF\xFF\xFF\xFF":
				if packetsegments[0][4:] == "infoResponse":
					self.data[INFO_STATUS] = self.__parseinfo(packetsegments[1])
					self.unrequire(INFO_STATUS)
				if packetsegments[0][4:] == "statusResponse":
					if self.data.has_key(INFO_STATUS):
						self.data[INFO_STATUS].update(self.__parseinfo(packetsegments[1]))
					self.data[INFO_PLAYER] = self.__parseplayer("\n".join(packetsegments[2:-1]))
					self.unrequire(INFO_PLAYER)

	def __parseinfo(self, data):
		information = {}
		variables = DataReader(data)
		variables.readto(0x5C)
		while variables.data:
			(name, value) = variables.readto(0x5C, 2)
			if name: information[name] = value
		return information
		
	def __parseplayer(self, data):
		information = []
		players = DataReader(data)
		while players.data:
			rawplayer = players.readto(0x0A)
			player = []
			while rawplayer:
				if rawplayer[0] == '\"':
					rawplayer = rawplayer[1:]
					end = rawplayer.find('"')
					player.append(rawplayer[0:end])
					rawplayer = rawplayer[end+1:]
				else:
					end = rawplayer.find(" ")
					if end == -1:
						player.append(rawplayer)
						rawplayer = ""
					else:
						player.append(rawplayer[0:end])
						rawplayer = rawplayer[end:]
				if rawplayer: rawplayer = rawplayer[1:]
			information.append(player)
		return information


class q4(none):

	"""
	Quake 4
	"""

	SUPPORTS = INFO_STATUS | INFO_PLAYER

	REQUEST_INFO		= "\xFF\xFFgetInfo\x00\x00\x00\x00\x00"

	def request(self, infotype, *args, **kwargs):
		super(q4, self).request(infotype, *args, **kwargs)
		if self.requires(INFO_STATUS | INFO_PLAYER):
			self.outbound.append(self.REQUEST_INFO)

	def parsepackets(self, packet, *args, **kwargs):
		super(q4, self).parsepackets(packet, *args, **kwargs)
		for packet in self.packets:
			self.packets.remove(packet)
			if packet[0:2] == "\xFF\xFF":
				if packet[2:14] == "infoResponse":
					self.data[INFO_STATUS] = self.__parseinfo(packet[15:])
					self.data[INFO_STATUS]['si_numPlayers'] = len(self.data[INFO_PLAYER])
					self.unrequire(INFO_STATUS | INFO_PLAYER)

	def __parseinfo(self, data):
		information = {}
		variables = DataReader(data)
		variables.read("8B")
		while variables.data:
			(name, value) = variables.readto(0x00, 2)
			if not name and not value: break
			information[name] = value
		self.data[INFO_PLAYER] = self.__parseplayer(variables.data)
		return information
		
	def __parseplayer(self, data):
		information = []
		players = DataReader(data)
		while players.data and not players.data[0] == " ":
			player = {}
			players.read("B")
			player["ping"]			= players.read("H")[0]
			player["rate"]			= players.read("H")[0]
			players.read("BB")
			player["playername"]	= players.readto(0x00)
			if not players.data[-5] == " ":
				player["clantag"]	= players.readto(0x00)
			information.append(player)
		return information


class qw(none):

	"""
	QuakeWorld
	"""

	SUPPORTS = INFO_STATUS | INFO_PLAYER

	REQUEST_INFO		= "\xFF\xFF\xFF\xFFstatus\x0A\x00"

	def request(self, infotype, *args, **kwargs):
		super(qw, self).request(infotype, *args, **kwargs)
		if self.requires(INFO_STATUS | INFO_PLAYER):
			self.outbound.append(self.REQUEST_INFO)

	def parsepackets(self, packet, *args, **kwargs):
		super(qw, self).parsepackets(packet, *args, **kwargs)
		for packet in self.packets:
			self.packets.remove(packet)
			if packet[0:4] == "\xFF\xFF\xFF\xFF":
				if packet[4] == "n":
					packetsegments = packet[5:].split("\n")
					self.data[INFO_STATUS] = self.__parseinfo(packetsegments[0])
					self.data[INFO_PLAYER] = self.__parseplayer("\n".join(packetsegments[1:-1]))
					self.unrequire(INFO_STATUS | INFO_PLAYER)

	def __parseinfo(self, data):
		information = {}
		variables = DataReader(data)
		variables.readto(0x5C)
		while variables.data:
			(name, value) = variables.readto(0x5C, 2)
			if name: information[name] = value
		return information
		
	def __parseplayer(self, data):
		information = []
		players = DataReader(data)
		while players.data:
			rawplayer = players.readto(0x0A)
			player = []
			while rawplayer:
				if rawplayer[0] == '\"':
					rawplayer = rawplayer[1:]
					end = rawplayer.find('"')
					player.append(rawplayer[0:end])
					rawplayer = rawplayer[end+1:]
				else:
					end = rawplayer.find(" ")
					if end == -1:
						player.append(rawplayer)
						rawplayer = ""
					else:
						player.append(rawplayer[0:end])
						rawplayer = rawplayer[end:]
				if rawplayer: rawplayer = rawplayer[1:]
			information.append(player)
		return information


class ase(none):

	"""
	All Seeing Eye
	"""

	SUPPORTS = INFO_STATUS | INFO_PLAYER

	REQUEST_INFO		= "\x73"

	def request(self, infotype, *args, **kwargs):
		super(ase, self).request(infotype, *args, **kwargs)
		if self.requires(INFO_STATUS | INFO_PLAYER):
			self.outbound.append(self.REQUEST_INFO)

	def parsepackets(self, packet, *args, **kwargs):
		super(ase, self).parsepackets(packet, *args, **kwargs)
		for packet in self.packets:
			self.packets.remove(packet)
			if packet[0:4] == "\x45\x59\x45\x31":
				self.data[INFO_STATUS] = self.__parseinfo(packet[4:])
				self.unrequire(INFO_STATUS | INFO_PLAYER)

	def __parseinfo(self, data):
		information = {}
		variables = DataReader(data)
		(
			information["gamename"],
			information["port"],
			information["hostname"],
			information["gametype"],
			information["mapname"],
			information["version"],
			information["password"],
			information["numplayers"],
			information["maxplayers"]
		) = self.__readstring(variables, 9)
		while variables.data:
			name = self.__readstring(variables, 1)[0]
			if not name: break
			information[name] = self.__readstring(variables, 1)[0]
		self.data[INFO_PLAYER] = self.__parseplayer(variables.data)
		return information
		
	def __parseplayer(self, data):
		information = []
		players = DataReader(data)
		while players.data:
			player = {}
			flags = players.read("B")[0]
			if flags & 1:
				player["playername"] = self.__readstring(players, 1)[0]
			if flags & 2:
				player["teamname"] = self.__readstring(players, 1)[0]
			if flags & 4:
				player["skin"] = self.__readstring(players, 1)[0]
			if flags & 8:
				player["score"] = self.__readstring(players, 1)[0]
			if flags & 16:
				player["ping"] = self.__readstring(players, 1)[0]
			if flags & 32:
				player["time"] = self.__readstring(players, 1)[0]
			information.append(player)
		return information


	def __readstring(self, data, count):
		value = tuple()
		for x in xrange(count):
			length = ord(data.data[0])
			value += (data.data[1:length],)
			data.data = data.data[length:]
		return value
