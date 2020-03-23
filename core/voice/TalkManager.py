import json
from pathlib import Path

import random

from core.base.model.Manager import Manager


class TalkManager(Manager):

	def __init__(self):
		super().__init__()
		self._langData = dict()


	@property
	def langData(self) -> dict:
		return self._langData


	def onStart(self):
		super().onStart()
		self.loadTalks()


	def loadTalks(self, skillToLoad: str = None):
		# Global System Talks
		if not skillToLoad:
			systemLangTalksMountpoint = Path('system/manager/TalkManager/talks')

			for systemLangTalkFile in systemLangTalksMountpoint.glob('*.json'):
				lang = systemLangTalkFile.stem
				self._langData.setdefault('system', dict())[lang] = json.loads(systemLangTalkFile.read_text())

		# Skill Talks
		skills = self.ConfigManager.skillsConfigurations

		for skillName in skills:
			if skillToLoad and skillToLoad != skillName:
				continue

			langTalksMountpoint = Path('skills', skillName, 'talks')
			if not langTalksMountpoint.exists():
				continue

			for langTalkFile in langTalksMountpoint.glob('*.json'):
				lang = langTalkFile.stem
				try:
					self._langData.setdefault(skillName, dict())[lang] = json.loads(langTalkFile.read_text())
				except FileNotFoundError:
					continue
				except ValueError as e:
					self.logError(f'{e}')
					continue


	def getTexts(self, skill, talk, strType='default') -> list:
		arr = list()
		try:
			skill = self.Commons.toCamelCase(skill)
			arr = self._langData[skill][self.LanguageManager.activeLanguage][talk][strType]
		except KeyError:
			self.logWarning(f'Was asked to return unexisting texts {talk} for skill {skill} with type {strType}')

		return arr


	def chooseTalk(self, talk: str, skill: str, activeLanguage: str, defaultLanguage: str, shortReplyMode: bool) -> str:
		try:
			talkData = self._langData[skill][activeLanguage][talk]

			# There's no short/long version?
			if isinstance(talkData, list):
				return random.choice(self._langData[skill][activeLanguage][talk])

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
				self.logError(f'Was asked to get "{talk}" from "{skill}" skill in "{activeLanguage}" but it doesn\'t exist, falling back to "{defaultLanguage}" version instead')
				# call itself again with default language and then exit because activeLanguage == defaultLanguage
				return self.chooseTalk(talk, skill, defaultLanguage, defaultLanguage, shortReplyMode)

			# Give up, that text does not exist...
			self.logError(f'Was asked to get "{talk}" from "{skill}" skill but language string doesn\'t exist')
			return ''


	def randomTalk(self, talk: str, skill: str = '', forceShortTalk: bool = False) -> str:
		"""
		Gets a random string to speak corresponding to talk string. If no skill provided it will use the caller's name
		:param talk:
		:param skill:
		:param forceShortTalk:
		:return:
		"""
		skill = skill or self.getFunctionCaller()
		if not skill:
			return ''

		shortReplyMode = forceShortTalk or self.UserManager.checkIfAllUser('sleeping') or self.ConfigManager.getAliceConfigByName('shortReplies')
		activeLanguage = self.LanguageManager.activeLanguage
		defaultLanguage = self.LanguageManager.defaultLanguage

		string = self.chooseTalk(talk, skill, activeLanguage, defaultLanguage, shortReplyMode)
		if not string:
			return ''


		if self.ConfigManager.getAliceConfigByName('whisperWhenSleeping') and \
			self.TTSManager.tts.getWhisperMarkup() and \
			self.UserManager.checkIfAllUser('sleeping'):

			start, end = self.TTSManager.tts.getWhisperMarkup()
			string = f'{start}{string}{end}'

		return string
