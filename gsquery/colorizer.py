OUTPUT_TEXT = 0
OUTPUT_HTML = 1
OUTPUT_ANSI = 2

class none:
	def __init__(self):
		self.mode = OUTPUT_TEXT
		
	def parse(self, string):
		return string

class q3(none):
	COLORS_HTML = {
		"0": "000000",
		"1": "DA0120",
		"2": "00B906",
		"3": "E8FF19",
		"4": "170BDB",
		"5": "23C2C6",
		"6": "E201DB",
		"7": "FFFFFF",
		"8": "CA7C27",
		"9": "757575",
		"a": "EB9F53",
		"b": "106F59",
		"c": "5A134F",
		"d": "035AFF",
		"e": "681EA7",
		"f": "5097C1",
		"g": "BEDAC4",
		"h": "024D2C",
		"i": "7D081B",
		"j": "90243E",
		"k": "743313",
		"l": "A7905E",
		"m": "555C26",
		"n": "AEAC97",
		"o": "C0BF7F",
		"p": "000000",
		"q": "DA0120",
		"r": "00B906",
		"s": "E8FF19",
		"t": "170BDB",
		"u": "23C2C6",
		"v": "E201DB",
		"w": "FFFFFF",
		"x": "CA7C27",
		"y": "757575",
		"z": "CC8034",
		"/": "DBDF70",
		"*": "BBBBBB",
		"-": "747228",
		"+": "993400",
		"?": "670504",
		"@": "623307",
	}
	
	COLORS_ANSI = {
		"0": "0;30m",
		"1": "0;31m",
		"2": "0;32m",
		"3": "1;33m",
		"4": "0;34m",
		"5": "1;34m",
		"6": "1;35m",
		"7": "1;37m",
		"8": "0;33m",
		"9": "1;30m",
	}

	def parse(self, string):
		currentcode = None
		output = ""
		while len(string) > 0:
			if string[0] == "^":
				output += self.parsecode(currentcode, string[1])
				currentcode = string[1]
				string = string[2:]
			else:
				output += string[0]
				string = string[1:]
		output += self.parsecode(currentcode)
		return output
	
	def parsecode(self, currentcode = None, newcode = None):
		output = ""
		if currentcode == newcode:
			pass
		elif self.mode == OUTPUT_TEXT:
			pass
		elif self.mode == OUTPUT_HTML:
			if not currentcode == None:
				output += "</span>"
			if self.COLORS_HTML.has_key(newcode):
				output += "<span style=\"color:#%s;\">" % (self.COLORS_HTML[newcode],)
		elif self.mode == OUTPUT_ANSI:
			if currentcode == None or newcode == None:
				output += "\033[0;0m"
			if self.COLORS_ANSI.has_key(newcode):
				output += "\033[%s" % (self.COLORS_ANSI[newcode],)
		return output

class unreal(none):
	def parse(self, string):
		currentcode = None
		output = ""
		while len(string) > 0:
			if ord(string[0]) == 27:
				output += self.parsecode(currentcode, string[1:4])
				currentcode = string[1:4]
				string = string[4:]
			else:
				output += string[0]
				string = string[1:]
		output += self.parsecode(currentcode)
		return output
	
	def parsecode(self, currentcode = None, newcode = None):
		output = ""
		if currentcode == newcode:
			pass
		elif self.mode == OUTPUT_TEXT:
			pass
		elif self.mode == OUTPUT_HTML:
			if not currentcode == None:
				output += "</span>"
			if not newcode == None:
				output += "<span style=\"color:rgb(%d,%d,%d);\">" % (ord(newcode[0]),ord(newcode[1]),ord(newcode[2]))
		elif self.mode == OUTPUT_ANSI:
			if currentcode == None or newcode == None:
				output += "\033[0;0m"
		return output
