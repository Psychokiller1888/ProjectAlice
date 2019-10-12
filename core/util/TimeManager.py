from datetime import datetime

from core.base.SuperManager import SuperManager
from core.base.model.Manager import Manager


class TimeManager(Manager):

	NAME = 'TimeManager'

	def __init__(self):
		super().__init__(self.NAME)


	def onBooted(self):
		self.timerSignal(self, 1, 'onFullMinute')
		self.timerSignal(self, 5, 'onFiveMinute')
		self.timerSignal(self, 15, 'onQuarterHour')
		self.timerSignal(self, 60, 'onFullHour')


	def timerSignal(self, minutes: int, signal: str, running: bool = False):
		if running:
			SuperManager.getInstance().broadcast(signal, exceptions=[self.NAME], propagateToModules=True)

		minute = datetime.now().minute
		second = datetime.now().second
		missingSeconds = 60 * (minutes - minute % minutes) - second
		self.ThreadManager.doLater(interval=missingSeconds, func=self.timerSignal, args=[minutes, signal, True])
