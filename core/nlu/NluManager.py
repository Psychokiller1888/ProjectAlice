from pathlib import Path

import shutil

from core.base.model.Manager import Manager


class NluManager(Manager):

	def __init__(self):
		super().__init__()
		self._nluEngine = None
		self._pathToCache = Path(self.Commons.rootDir(), 'var/cache/nlu/trainingData')
		self.selectNluEngine()


	def onStart(self):
		super().onStart()
		if not self._pathToCache.exists():
			self._pathToCache.mkdir(parents=True)

		self.isTrainingNeeded()


	def onStop(self):
		super().onStop()

		if self._nluEngine:
			self._nluEngine.stop()


	def afterSkillChange(self):
		self.isTrainingNeeded()


	def isTrainingNeeded(self):
		if not Path(self.Commons.rootDir(), f'assistant/nlu_engine').exists():
			if Path(self.Commons.rootDir(), f'trained/assistants/assistant_{self.LanguageManager.activeLanguage}/nlu_engine').exists():
				self.SnipsAssistantManager.linkAssistant()
			else:
				self.DialogTemplateManager.clearCache()

		if self.DialogTemplateManager.hasChanges:
			self.buildTrainingData(self.DialogTemplateManager.updatedData)
			self.trainNLU()


	def selectNluEngine(self):
		if self._nluEngine:
			self._nluEngine.stop()

		if self.ConfigManager.getAliceConfigByName('nluEngine') == 'snips':
			from core.nlu.model.SnipsNlu import SnipsNlu

			self._nluEngine = SnipsNlu()
		else:
			self.logFatal(f'Unsupported NLU engine: {self.ConfigManager.getAliceConfigByName("nluEngine")}')
			self.ProjectAlice.onStop()
			return

		self._nluEngine.start()


	def buildTrainingData(self, changes: dict):
		for changedSkill, changedLanguages in changes.items():
			if not changedSkill.startswith('--'):
				pathToSkillResources = Path(self.Commons.rootDir(), f'skills/{changedSkill}/dialogTemplate')

				for lang in changedLanguages:
					self._nluEngine.convertDialogTemplate(pathToSkillResources / f'{lang}.json')
			else:
				skillName = changedSkill.replace('--', '')

				if not changedLanguages:
					for file in Path(self.Commons.rootDir(), '/var/cache/nlu/trainingData/').glob(f'{skillName}_'):
						file.unlink()
				else:
					for lang in changedLanguages:
						langFile = Path(self.Commons.rootDir(), f'/var/cache/nlu/trainingData/{skillName}_{lang}.json')
						if langFile.exists():
							langFile.unlink()


	def trainNLU(self):
		self._nluEngine.train()


	def clearCache(self):
		shutil.rmtree(self._pathToCache)
		self._pathToCache.mkdir()
