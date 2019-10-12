import logging

from core.commons import commons


class Logger:

	def __init__(self, *args, **kwargs):
		self._logger = logging.getLogger('ProjectAlice')


	def logInfo(self, msg: str):
		self.doLog(function='info', msg=msg)


	def logError(self, msg: str):
		self.doLog(function='error', msg=msg)


	def logDebug(self, msg: str):
		self.doLog(function='debug', msg=msg)


	def logFatal(self, msg: str):
		self.doLog(function='fatal', msg=msg)


	def logWarning(self, msg: str):
		self.doLog(function='warning', msg=msg)


	def logCritical(self, msg: str):
		self.doLog(function='critical', msg=msg)


	def doLog(self, function: callable, msg: str):
		func = getattr(self._logger, function)
		func(self.decorate(msg), exc_info=True)


	@staticmethod
	def decorate(msg: str) -> str:
		return f'[{commons.getFunctionCaller()}] {msg}'