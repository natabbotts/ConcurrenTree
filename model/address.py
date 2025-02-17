from ConcurrenTree.model import ModelBase
import re
import json

class Address(ModelBase):
	''' Address format: [4,"hello"," dolly"] '''

	def __init__(self, target=[]):
		if type(target)==list:
			self.parse(target)
		elif isinstance(target, Address):
			self.layers = target.layers
		elif type(target) in (str, unicode):
			self.layers = json.loads(target)
		else:
			raise TypeError("Expected list or address.Address, got "+str(type(target)))

	def parse(self, l):
		''' Does not check for syntax errors yet '''
		self.layers = []
		pos = None
		for i in expand(l):
			if type(i)==int:
				pos = i
			else:
				if pos==None:
					self.layers.append(i)
				else:
					self.layers.append((pos,i))
					pos = None

	def resolve(self, tree):
		x = tree
		error = 0
		for i in self.layers:
			error += 1
			if type(i) in (str, unicode):
				i = (len(x), i)
			try:
				x = x.get(i[0],i[1])
			except BeyondFlatError as e:
				raise BeyondFlatError(Address(self.layers[:error]))
		return x


	def proto(self):
		return expand(self.layers)

	def prepend(self, value):
		''' Value may be a 2-tuple or a string '''
		self.layers.insert(0,value)

	def jump(self, pos, max, key):
		if pos==max:
			return key
		else:
			return pos, key

	def __eq__(self, other):
		return self.layers == other.layers

	def __ne__(self, other):
		return self.layers != other.layers

	__hash__ = None

	def __repr__(self):
		classname = repr(self.__class__).split()[1]
		return "<%s instance %s at %s>" % (classname, str(self), hex(long(id(self)))[:-1])

class BeyondFlatError(Exception):
	def __init__(self, flataddr):
		''' Flataddr should be the address of the node that needs to be loaded. '''
		Exception.__init__(self, "Target flat not loaded: "+str(flataddr))
		self.addr = flataddr

	def propogate(self, pos, max, value):
		self.addr.prepend(self.addr.jump(pos, max, value))
		raise BeyondFlatError(self.addr)

def expand(l):
	''' Expands all sub-lists '''
	result = []
	for i in l:
		if type(i) in (tuple, list):
			result += list(i)
		else:
			result.append(i)
	return result
