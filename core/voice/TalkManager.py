import json
import random
from pathlib import Path

from core.base.model.Manager import Manager


class TalkManager(Manager):

	NAME = 'TalkManager'

	def __init__(self):
		super().__init__(self.NAME)
		self._langData = dict()


	@property
	def langData(self) -> dict:
		return self._langData


	def onStart(self):
		super().onStart()
		self.loadTalks()


	def loadTalks(self, moduleToLoad: str = None):
		# Global System Talks
		if not moduleToLoad:
			systemLangTalksMountpoint = Path('system/manager/TalkManager/talks')

			for systemLangTalkFile in systemLangTalksMountpoint.iterdir():
				lang = systemLangTalkFile.stem
				self._langData.setdefault('system', dict())[lang] = json.loads(systemLangTalkFile.read_text())

		# Module Talks
		modules = self.ConfigManager.modulesConfigurations

		for skillName in modules:
			if moduleToLoad and moduleToLoad != skillName:
				continue

			langTalksMountpoint = Path('modules', skillName, 'talks')
			if not langTalksMountpoint.exists():
				continue

			for langTalkFile in langTalksMountpoint.iterdir():
				lang = langTalkFile.stem
				try:
					self._langData.setdefault(skillName, dict())[lang] = json.loads(langTalkFile.read_text())
				except FileNotFoundError:
					continue
				except ValueError:
					continue


	def getTexts(self, module, talk, strType='default') -> list:
		arr = list()
		try:
			module = self.Commons.toCamelCase(module)
			arr = self._langData[module][self.LanguageManager.activeLanguage][talk][strType]
		except KeyError:
			self.logWarning(f'Was asked to return unexisting texts {talk} for module {module} with type {strType}')

		return arr


	def chooseTalk(self, talk: str, module: str, activeLanguage: str, defaultLanguage: str, shortReplyMode: bool) -> str:
		try:
			talkData = self._langData[module][activeLanguage][talk]

			# There's no short/long version?
			if isinstance(talkData, list):
				return random.choice(self._langData[module][activeLanguage][talk])

			if shortReplyMode:
				try:
					return random.choice(talkData['short'])
				except KeyError:
					return random.choice(talkData['default'])
			else:
				return random.choice(talkData['default'])
		except KeyError:
			# Fallback to default language then
			if activeLanguage != defaultLanguage:
				self.logError(f'Was asked to get "{talk}" from "{module}" module in "{activeLanguage}" but it doesn\'t exist, falling back to "{defaultLanguage}" version instead')
				# call itself again with default language and then exit because activeLanguage == defaultLanguage
				return self.chooseTalk(talk, module, defaultLanguage, defaultLanguage, shortReplyMode)

			# Give up, that text does not exist...
			self.logError(f'Was asked to get "{talk}" from "{module}" module but language string doesn\'t exist')
			return ''


	def randomTalk(self, talk: str, module: str = '', forceShortTalk: bool = False) -> str:
		"""
		Gets a random string to speak corresponding to talk string. If no module provided it will use the caller's name
		:param talk:
		:param module:
		:param forceShortTalk:
		:return:
		"""
		module = module or self.getFunctionCaller()
		if not module:
			return ''

		shortReplyMode = forceShortTalk or self.UserManager.checkIfAllUser('sleeping') or self.ConfigManager.getAliceConfigByName('shortReplies')
		activeLanguage = self.LanguageManager.activeLanguage
		defaultLanguage = self.LanguageManager.defaultLanguage

		string = self.chooseTalk(talk, module, activeLanguage, defaultLanguage, shortReplyMode)
		if not string:
			return ''


		if self.ConfigManager.getAliceConfigByName('whisperWhenSleeping') and \
			self.TTSManager.tts.getWhisperMarkup() and \
			self.UserManager.checkIfAllUser('sleeping'):

			start, end = self.TTSManager.tts.getWhisperMarkup()
			string = f'{start}{string}{end}'

		return string
