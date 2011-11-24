import socket, struct

class DataReader:
	def __init__(self, data):
		self.data = data

	def read(self, format, byteorder = "<"):
		size = struct.calcsize(byteorder + format)
		if len(self.data) >= size:
			value = struct.unpack(byteorder + format, self.data[0:size])
			self.data = self.data[size:]
		else:
			value = tuple('') * len(format)
		return value

	def readto(self, byte, count = None):
		value = tuple()
		values = 1
		if not count == None:
			values = count
		for x in xrange(values):
			index = self.data.find(chr(byte))
			if index == -1:
				index = len(self.data)
			value += (self.data[0:index],)
			self.data = self.data[index+1:]
		if count == None:
			value = value[0]
		return value
