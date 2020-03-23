import threading
from pathlib import Path
from threading import Event
from typing import Optional

import pkg_resources

from core.asr.model.Recorder import Recorder
from core.base.model.ProjectAliceObject import ProjectAliceObject
from core.commons import constants
from core.dialog.model.DialogSession import DialogSession


class ASR(ProjectAliceObject):
	NAME = 'Generic ASR'
	DEPENDENCIES = dict()


	def __init__(self):
		self._capableOfArbitraryCapture = False
		self._isOnlineASR = False
		self._timeout = Event()
		self._timeoutTimer: Optional[threading.Timer] = None
		self._recorder: Optional[Recorder] = None
		super().__init__()


	@property
	def capableOfArbitraryCapture(self) -> bool:
		return self._capableOfArbitraryCapture


	@property
	def isOnlineASR(self) -> bool:
		return self._isOnlineASR


	def checkDependencies(self) -> bool:
		self.logInfo('Checking dependencies')
		try:
			pkg_resources.require(self.DEPENDENCIES['pip'])
			return True
		except:
			self.logInfo('Found missing dependencies')
			return False


	def install(self) -> bool:
		self.logInfo('Installing dependencies')

		try:
			for dep in self.DEPENDENCIES['system']:
				self.logInfo(f'Installing "{dep}"')
				self.Commons.runRootSystemCommand(['apt-get', 'install', '-y', dep])
				self.logInfo(f'Installed!')

			for dep in self.DEPENDENCIES['pip']:
				self.logInfo(f'Installing "{dep}"')
				self.Commons.runSystemCommand(['./venv/bin/pip', 'install', dep])
				self.logInfo(f'Installed!')

			return True
		except Exception as e:
			self.logError(f'Installing dependencies failed: {e}')
			return False


	def onStart(self):
		self.logInfo(f'Starting {self.NAME}')


	def onStop(self):
		self.logInfo(f'Stopping {self.NAME}')
		self._timeout.set()


	def onStartListening(self, session):
		self.MqttManager.mqttClient.subscribe(constants.TOPIC_AUDIO_FRAME.format(session.siteId))


	def decodeFile(self, filepath: Path, session: DialogSession):
		pass


	def decodeStream(self, session: DialogSession):
		self._timeout.clear()
		self._timeoutTimer = self.ThreadManager.newTimer(interval=int(self.ConfigManager.getAliceConfigByName('asrTimeout')), func=self.timeout)


	def end(self, session: DialogSession):
		self.MqttManager.mqttClient.unsubscribe(constants.TOPIC_AUDIO_FRAME.format(session.siteId))
		self._recorder.stopRecording()
		if self._timeoutTimer and self._timeoutTimer.is_alive():
			self._timeoutTimer.cancel()


	def timeout(self):
		self._timeout.set()
		self.logWarning('ASR timed out')


	def checkLanguage(self) -> bool:
		return True


	def downloadLanguage(self) -> bool:
		return False


	def partialTextCaptured(self, session: DialogSession, text: str, likelihood: float, seconds: float):
		self.MqttManager.partialTextCaptured(session, text, likelihood, seconds)
