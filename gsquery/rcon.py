from __init__ import *

class none(object):

	def __init__(self, hostname, port):
		self.host		= (socket.gethostbyname(hostname), int(port))
		self.socket	= socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.requestid	= 1337
		
		self.socket.settimeout(4)
		self.socket.connect(self.host)
		
class hl2(none):

	SERVERDATA_EXECCOMMAND	= 2
	SERVERDATA_AUTH		= 3
	SERVERDATA_RESPONSE_VALUE	= 0
	SERVERDATA_AUTH_RESPONSE	= 2
	
	def __encodeint(self, integer):
		return str(struct.pack("i", integer))
	
	def __decodeint(self, integer):
		return struct.unpack("i", integer)[0]
	
	def __sendrcon(self, requestcommand, string1 = "", string2 = ""):
		commandlength = 10 + len(string1) + len(string2)
		fullcommand = self.__encodeint(commandlength) + self.__encodeint(self.requestid) + self.__encodeint(requestcommand) + string1 + "\x00" + string2 + "\x00"
		
		self.socket.send(fullcommand)

		fullresponse = self.socket.recv(4096)
		(fullresponse, responselength) = (fullresponse[4:], self.__decodeint(fullresponse[0:4]))
		
		while len(fullresponse) < responselength:
			try:
				fullresponse += self.socket.recv(4096)
			except:
				return None
		
		responseid = self.__decodeint(fullresponse[0:4])
		responsecommand = self.__decodeint(fullresponse[4:8])

		print responseid, responsecommand, repr(fullresponse)

		if responsecommand == self.SERVERDATA_RESPONSE_VALUE:
			if responseid == self.requestid:
				return fullresponse[8:-1].split("\x00")
			else:
				return None
		elif responsecommand == self.SERVERDATA_AUTH_RESPONSE:
			if responseid == self.requestid: return True
			elif responseid == -1: return False
			else: return None
		else:
			return None
	
	def authenticate(self, password):
		response = self.__sendrcon(self.SERVERDATA_AUTH, password)
		print response
		if response is True: print "Authenticated"
		elif response is False: print "Invalid Password"
	
	def command(self, command):
		self.__sendrcon(self.SERVERDATA_EXECCOMMAND, command)
	

a = hl2("66.225.195.179", 27015)
a.authenticate("Testing rcon so i needed a server so i chose yours! sorry.")
