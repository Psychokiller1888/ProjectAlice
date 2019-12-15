from __future__ import annotations

import importlib
import inspect
import json
import sqlite3
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Tuple, Optional

import re
from paho.mqtt import client as MQTTClient

from core.ProjectAliceExceptions import AccessLevelTooLow, SkillStartingFailed
from core.base.model import Widget
from core.base.model.Intent import Intent
from core.base.model.ProjectAliceObject import ProjectAliceObject
from core.commons import constants
from core.dialog.model.DialogSession import DialogSession
from core.user.model.AccessLevels import AccessLevel


class AliceSkill(ProjectAliceObject):

	#TODO: authOnly should be a parameter of the intents, so it can be e.g. passed along with the IntentHandler
	# decorator
	def __init__(self, supportedIntents: Iterable = None, authOnlyIntents: dict = None, databaseSchema: dict = None):
		super().__init__(logDepth=4)
		try:
			path = Path(inspect.getfile(self.__class__)).with_suffix('.install')
			self._install = json.loads(path.read_text())
		except FileNotFoundError:
			raise SkillStartingFailed(error=f'[{type(self).__name__}] Cannot find install file')
		except Exception as e:
			raise SkillStartingFailed(error=f'[{type(self).__name__}] Failed loading skill: {e}')

		self._name = self._install['name']
		self._author = self._install['author']
		self._version = self._install['version']
		self._updateAvailable = False
		self._active = True
		self._delayed = False
		self._required = False
		self._databaseSchema = databaseSchema
		self._widgets = dict()

		self._supportedIntents: Dict[str, Intent] = self.buildIntentList(
			supportedIntents or list(),
			authOnlyIntents or dict())

		self._utteranceSlotCleaner = re.compile('{(.+?):=>.+?}')
		self.loadWidgets()


	def buildIntentList(self, supportedIntents, authOnlyIntents) -> dict:
		intents: Dict[str, Intent] = self.findDecoratedIntents()
		for item in supportedIntents:
			if isinstance(item, tuple):
				item[0].fallbackFunction = item[1]
				item = item[0]
			elif isinstance(item, str):
				item = Intent(item, userIntent=False)

			if str(item) in intents:
				intents[str(item)].addDialogMapping(item.dialogMapping)
				if item.fallbackFunction:
					intents[str(item)].fallbackFunction = item.fallbackFunction
			else:
				intents[str(item)] = intent
		
		for intent, level in authOnlyIntents.items():
			if str(intent) in intents:
				intents[str(item)].authOnly = level
		
		return intents

	
	@classmethod
	def findDecoratedIntents(cls) -> dict:
		intentMappings = dict()
		for name in dir(cls):
			function = getattr(cls, name)
			intents = getattr(function, 'intents', list())
			for intentMapping in intents:
				intent = intentMapping['intent']
				requiredState = intentMapping['requiredState']
				if str(intent) not in intentMappings:
					intentMappings[str(intent)] = intent
				
				if requiredState:
					intentMappings[str(intent)].addDialogMapping({requiredState: function})
				else:
					intentMappings[str(intent)].fallbackFunction = function

		return intentMappings


	# noinspection SqlResolve
	def loadWidgets(self):
		fp = Path(self.getCurrentDir(), 'widgets')
		if fp.exists():
			self.logInfo(f"Loading {len(list(fp.glob('*.py'))) - 1} widgets")

			data = self.DatabaseManager.fetch(
				tableName='widgets',
				query='SELECT * FROM :__table__ WHERE parent = :parent ORDER BY `zindex`',
				callerName=self.SkillManager.name,
				values={'parent': self.name},
				method='all'
			)
			if data:
				data = {row['name']: row for row in data}

			for file in fp.glob('*.py'):
				if file.name.startswith('__'):
					continue

				widgetName = Path(file).stem
				widgetImport = importlib.import_module(f'skills.{self.name}.widgets.{widgetName}')
				klass = getattr(widgetImport, widgetName)

				if widgetName in data: # widget already exists in DB
					widget = klass(data[widgetName])
					self._widgets[widgetName] = widget
					widget.setParentSkillInstance(self)
					del data[widgetName]
					self.logInfo(f'Loaded widget "{widgetName}"')

				else: # widget is new
					self.logInfo(f'Adding widget "{widgetName}"')
					widget = klass({
						'name': widgetName,
						'parent': self.name,
					})
					self._widgets[widgetName] = widget
					widget.setParentSkillInstance(self)
					widget.saveToDB()

			for widgetName in data: # deprecated widgets
				self.logInfo(f'Widget "{widgetName}" is deprecated, removing')
				self.DatabaseManager.delete(
					tableName='widgets',
					callerName=self.SkillManager.name,
					query='DELETE FROM :__table__ WHERE parent = :parent AND name = :name',
					values={
						'parent': self.name,
						'name': widgetName
					}
				)


	def getWidgetInstance(self, widgetName: str) -> Optional[Widget]:
		return self._widgets.get(widgetName)


	def getUtterancesByIntent(self, intent: Intent, forceLowerCase: bool = True, cleanSlots: bool = False) -> list:
		utterances = list()

		if isinstance(intent, tuple):
			check = intent[0].justAction
		elif isinstance(intent, Intent):
			check = intent.justAction
		else:
			check = intent.split('/')[-1].split(':')[-1]

		for dtIntentName, dtSkillName in self.SamkillaManager.dtIntentNameSkillMatching.items():
			if dtIntentName == check and dtSkillName == self.name:

				for utterance in self.SamkillaManager.dtIntentsSkillsValues[dtIntentName]['utterances']:
					if cleanSlots:
						utterance = re.sub(self._utteranceSlotCleaner, '\\1', utterance)

					utterances.append(utterance.lower() if forceLowerCase else utterance)

		return utterances


	def getCurrentDir(self):
		return Path(inspect.getfile(self.__class__)).parent


	@property
	def widgets(self) -> dict:
		return self._widgets


	@property
	def active(self) -> bool:
		return self._active


	@active.setter
	def active(self, value: bool):
		self._active = value


	@property
	def name(self) -> str:
		return self._name


	@name.setter
	def name(self, value: str):
		self._name = value


	@property
	def author(self) -> str:
		return self._author


	@author.setter
	def author(self, value: str):
		self._author = value


	@property
	def version(self) -> float:
		return self._version


	@version.setter
	def version(self, value: float):
		self._version = value


	@property
	def updateAvailable(self) -> bool:
		return self._updateAvailable


	@updateAvailable.setter
	def updateAvailable(self, value: bool):
		self._updateAvailable = value


	@property
	def required(self) -> bool:
		return self._required


	@required.setter
	def required(self, value: bool):
		self._required = value


	@property
	def supportedIntents(self) -> dict:
		return self._supportedIntents


	@supportedIntents.setter
	def supportedIntents(self, value: list):
		self._supportedIntents = value


	@property
	def delayed(self) -> bool:
		return self._delayed


	@delayed.setter
	def delayed(self, value: bool):
		self._delayed = value


	def subscribe(self, mqttClient: MQTTClient):
		for intent in self._supportedIntents:
			try:
				mqttClient.subscribe(str(intent))
			except:
				self.logError(f'Failed subscribing to intent "{str(intent)}"')


	def notifyDevice(self, topic: str, uid: str = '', siteId: str = ''):
		if uid:
			self.MqttManager.publish(topic=topic, payload={'uid': uid})
		elif siteId:
			self.MqttManager.publish(topic=topic, payload={'siteId': siteId})
		else:
			self.logWarning('Tried to notify devices but no uid or site id specified')


	def authentifcateIntent(self, session: DialogSession):
		intent = self._supportedIntents[session.intentName]
		# Return if intent is for auth users only but the user is unknown
		if session.user == constants.UNKNOWN_USER:
			self.endDialog(
				sessionId=session.sessionId,
				text=self.TalkManager.randomTalk(talk='unknowUser', skill='system')
			)
			raise AccessLevelTooLow()
		# Return if intent is for auth users only and the user doesn't have the accesslevel for it
		if not self.UserManager.hasAccessLevel(session.user, intent.authOnly):
			self.endDialog(
				sessionId=session.sessionId,
				text=self.TalkManager.randomTalk(talk='noAccess', skill='system')
			)
			raise AccessLevelTooLow()


	def dispatchMessage(self, session: DialogSession) -> bool:
		# Return if the skill isn't active
		if not self.active:
			return False
		
		if session.intentName not in self._supportedIntents:
			return False
		
		intent = self._supportedIntents[session.intentName]
		if intent.authOnly:
			authentifcateIntent(session)

		function = intent.getMapping(session) or self.onMessage
		return function(session=session)


	def getResource(self, skillName: str = '', resourcePathFile: str = '') -> Path:
		return Path(self.Commons.rootDir(), 'skills', skillName or self.name, resourcePathFile)


	def _initDB(self) -> bool:
		if self._databaseSchema:
			return self.DatabaseManager.initDB(schema=self._databaseSchema, callerName=self.name)
		return True


	def onStart(self) -> dict:
		if not self._active:
			self.logInfo(f'Skill {self.name} is not active')
		else:
			self.logInfo(f'Starting {self.name} skill')

		self._initDB()
		self.MqttManager.subscribeSkillIntents(self.name)
		return self._supportedIntents


	def onBooted(self) -> bool:
		if self.delayed:
			if self.ThreadManager.getEvent('SnipsAssistantDownload').isSet():
				self.ThreadManager.doLater(interval=5, func=self.onBooted)
				return False

			self.logInfo('Delayed start')
			self.ThreadManager.doLater(interval=5, func=self.onStart)

		return True


	def onSkillInstalled(self):
		self._updateAvailable = False
		#self.MqttManager.subscribeSkillIntents(self.name)


	def onSkillUpdated(self):
		self._updateAvailable = False
		#self.MqttManager.subscribeSkillIntents(self.name)


	# HELPERS
	def getConfig(self, key: str) -> Any:
		return self.ConfigManager.getSkillConfigByName(skillName=self.name, configName=key)


	def getSkillConfigs(self, withInfo: bool = False) -> dict:
		skillConfigs = self.ConfigManager.getSkillConfigs(self.name)
		if not withInfo:
			infoSettings = self.ConfigManager.aliceSkillConfigurationKeys
			skillConfigs = {key: value for key, value in skillConfigs.items() if key not in infoSettings}

		return skillConfigs


	def getSkillConfigsTemplate(self) -> dict:
		return self.ConfigManager.getSkillConfigsTemplate(self.name)


	def updateConfig(self, key: str, value: Any):
		self.ConfigManager.updateSkillConfigurationFile(skillName=self.name, key=key, value=value)


	def getAliceConfig(self, key: str) -> Any:
		return self.ConfigManager.getAliceConfigByName(configName=key)


	def updateAliceConfig(self, key: str, value: Any):
		self.ConfigManager.updateAliceConfiguration(key=key, value=value)


	def activeLanguage(self) -> str:
		return self.LanguageManager.activeLanguage


	def defaultLanguage(self) -> str:
		return self.LanguageManager.defaultLanguage


	def databaseFetch(self, tableName: str, query: str, values: dict = None, method: str = 'one') -> sqlite3.Row:
		return self.DatabaseManager.fetch(tableName=tableName, query=query, values=values, callerName=self.name, method=method)


	def databaseInsert(self, tableName: str, query: str = None, values: dict = None) -> int:
		return self.DatabaseManager.insert(tableName=tableName, query=query, values=values, callerName=self.name)


	def randomTalk(self, text: str, replace: list = None) -> str:
		talk = self.TalkManager.randomTalk(talk=text, skill=self.name)

		if replace:
			talk = talk.format(*replace)
		return talk


	def getSkillInstance(self, skillName: str) -> AliceSkill:
		return self.SkillManager.getSkillInstance(skillName=skillName)


	def say(self, text: str, siteId: str = constants.DEFAULT_SITE_ID, customData: dict = None, canBeEnqueued: bool = True):
		self.MqttManager.say(text=text, client=siteId, customData=customData, canBeEnqueued=canBeEnqueued)


	def ask(self, text: str, siteId: str = constants.DEFAULT_SITE_ID, intentFilter: list = None, customData: dict = None, previousIntent: str = '', canBeEnqueued: bool = True, currentDialogState: str = ''):
		self.MqttManager.ask(text=text, client=siteId, intentFilter=intentFilter, customData=customData, previousIntent=previousIntent, canBeEnqueued=canBeEnqueued, currentDialogState=currentDialogState)


	def continueDialog(self, sessionId: str, text: str, customData: dict = None, intentFilter: list = None, previousIntent: str = '', slot: str = '', currentDialogState: str = ''):
		self.MqttManager.continueDialog(sessionId=sessionId, text=text, customData=customData, intentFilter=intentFilter, previousIntent=str(previousIntent), slot=slot, currentDialogState=currentDialogState)


	def endDialog(self, sessionId: str = '', text: str = '', siteId: str = ''):
		self.MqttManager.endDialog(sessionId=sessionId, text=text, client=siteId)


	def endSession(self, sessionId):
		self.MqttManager.endSession(sessionId=sessionId)


	def playSound(self, soundFilename: str, location: Path = None, sessionId: str = '', siteId: str = constants.DEFAULT_SITE_ID, uid: str = ''):
		self.MqttManager.playSound(soundFilename=soundFilename, location=location, sessionId=sessionId, siteId=siteId, uid=uid)


	def publish(self, topic: str, payload: dict = None, qos: int = 0, retain: bool = False):
		self.MqttManager.publish(topic=topic, payload=payload, qos=qos, retain=retain)


	def decorate(self, msg: str, depth: int) -> str:
		"""
		overwrite Logger decoration method, since it should always
		be the skill name
		"""
		return f'[{self.name}] {msg}'


	def toJson(self) -> dict:
		return {
			'name': self._name,
			'author': self._author,
			'version': self._version,
			'updateAvailable': self._updateAvailable,
			'active': self._active,
			'delayed': self._delayed,
			'required': self._required,
			'databaseSchema': self._databaseSchema
		}
