import re

from core.commons import commons


#
# InputOption is a command line option (--option)
#
class InputOption:
	VALUE_NONE = 1
	VALUE_REQUIRED = 2
	VALUE_OPTIONAL = 4
	VALUE_IS_ARRAY = 8


	def __init__(self, name, shortcut, mode, description, default=None):
		if name.startswith('--'):
			name = name[2:]

		if name is None:
			raise ValueError('An option name cannot be empty.')

		reg = re.compile(r'-')

		if shortcut is not None:
			if isinstance(shortcut, list):
				for short in shortcut:
					# noinspection PyUnusedLocal
					short = re.sub(reg, '', short)  # weird

				shortcut = '|'.join(shortcut)
			else:
				shortcut = re.sub(reg, '', shortcut)

		if mode is None:
			mode = self.VALUE_NONE
		elif not int(mode) or mode > 15 or mode < 1:
			raise ValueError('Option mode {} is not valid.'.format(mode))

		self._name = name
		self.shortcut = shortcut
		self.mode = mode
		self.description = description
		self.default = list()

		if self.isArray() and not self.acceptValue():
			raise ValueError('Impossible to have an option mode VALUE_IS_ARRAY if the option does not accept a value.')

		self.setDefault(default)


	def getShortcut(self):
		return self.shortcut


	@property
	def name(self) -> str:
		return self._name



	def acceptValue(self) -> bool:
		return self.isValueRequired() or self.isValueOptional()


	def isValueRequired(self) -> bool:
		return self.mode == self.VALUE_REQUIRED


	def isValueOptional(self) -> bool:
		return self.mode == self.VALUE_OPTIONAL


	def isArray(self) -> bool:
		return self.mode == self.VALUE_IS_ARRAY


	def setDefault(self, default):

		if self.mode == self.VALUE_NONE and default is not None:
			raise ValueError('Cannot set a default value when using InputOption.VALUE_NONE mode.')

		if self.isArray():
			if default is None:
				default = list()
			elif not isinstance(default, list):
				raise ValueError('A default value for an array option must be an array.')

		if self.acceptValue():
			self.default = default
		else:
			self.default = False


	def getDefault(self):
		return self.default


	def getDescription(self):
		return self.description


	def equals(self, option):
		return option.name == self.name and \
			   option.getShortcut() == self.getShortcut() and \
			   option.getDefault() == self.getDefault() and \
			   option.isArray() == self.isArray() and \
			   option.isValueRequired() == self.isValueRequired() and \
			   option.isValueOptional() == self.isValueOptional()
