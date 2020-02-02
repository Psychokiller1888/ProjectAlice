from pathlib import Path

import requests

from core.base.SuperManager import SuperManager
from core.base.model.Version import Version
from core.commons import constants
from core.commons.model.Singleton import Singleton
from core.util.Stopwatch import Stopwatch


class ProjectAlice(Singleton):
	NAME = 'ProjectAlice'


	def __init__(self, restartHandler: callable):
		Singleton.__init__(self, self.NAME)
		self.log.info('Starting up Project Alice')
		self._booted = False
		with Stopwatch() as stopWatch:
			self._restart = False
			self._restartHandler = restartHandler
			self._superManager = SuperManager(self)

			self._superManager.initManagers()
			self._superManager.onStart()

			if self._superManager.configManager.getAliceConfigByName('useSLC'):
				self._superManager.commons.runRootSystemCommand(['systemctl', 'start', 'hermesledcontrol'])

			self._superManager.onBooted()
		self.log.info(f'- Started Project Alice in {stopWatch} seconds')
		self._booted = True


	@property
	def name(self) -> str:
		return self.NAME


	@property
	def isBooted(self) -> bool:
		return self._booted


	@property
	def restart(self) -> bool:
		return self._restart


	@restart.setter
	def restart(self, value: bool):
		self._restart = value


	def doRestart(self):
		self._restart = True
		self.onStop()


	def onStop(self):
		self.log.info('Shutting down Project Alice')
		self._superManager.onStop()
		if self._superManager.configManager.getAliceConfigByName('useSLC'):
			self._superManager.commons.runRootSystemCommand(['systemctl', 'stop', 'hermesledcontrol'])

		self.INSTANCE = None
		self._restartHandler()


	def updateProjectAlice(self):
		self.log.info('Checking Project Alice updates')
		req = requests.get(url='https://api.github.com/repos/project-alice-assistant/ProjectAlice/branches', auth=SuperManager.getInstance().configManager.getGithubAuth())
		if req.status_code != 200:
			self.log.warning('Failed checking for updates')
			return

		userUpdatePref = SuperManager.getInstance().configManager.getAliceConfigByName('aliceUpdateChannel')

		if userUpdatePref == 'master':
			candidate = 'master'
		else:
			candidate = Version.fromString(constants.VERSION)
			for branch in req.json():
				repoVersion = Version.fromString(branch['name'])
				if not repoVersion.isVersionNumber:
					continue

				releaseType = repoVersion.releaseType
				if userUpdatePref == 'rc' and releaseType in {'b', 'a'} or userUpdatePref == 'beta' and releaseType == 'a':
					continue

				if repoVersion > candidate:
					candidate = repoVersion

		self.log.info(f'Checking on "{str(candidate)}" update channel')
		commons = SuperManager.getInstance().commons
		commons.runSystemCommand(['git', '-C', commons.rootDir(), 'stash'])
		commons.runSystemCommand(['git', '-C', commons.rootDir(), 'clean', '-df'])
		commons.runSystemCommand(['git', '-C', commons.rootDir(), 'checkout', str(candidate)])
		commons.runSystemCommand(['git', '-C', commons.rootDir(), 'pull'])

		# Remove install tickets
		[file.unlink() for file in Path(commons.rootDir(), 'system/skillInstallTickets').glob('*') if file.is_file()]
