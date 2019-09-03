import json
import time
from pathlib import Path

import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from core.commons import commons
from core.snips.samkilla.Assistant import Assistant
from core.snips.samkilla.Entity import Entity
from core.snips.samkilla.Intent import Intent
from core.snips.samkilla.Skill import Skill
from core.ProjectAliceExceptions import AssistantNotFoundError, HttpError
from core.snips.samkilla.models.EnumSkillImageUrl import EnumSkillImageUrl as EnumSkillImageUrlClass
from core.snips.samkilla.processors.MainProcessor import MainProcessor

EnumSkillImageUrl = EnumSkillImageUrlClass()

import core.base.Managers as managers
from core.base.Manager import Manager

class SamkillaManager(Manager):

	NAME = 'SamkillaManager'
	ROOT_URL = "https://console.snips.ai"

	def __init__(self, mainClass, devMode: bool = True):
		super().__init__(mainClass, self.NAME)
		managers.SamkillaManager = self

		self._currentUrl = ''
		self._browser = None
		self._devMode = devMode
		self._cookie = ''
		self._userId = ''
		self._userEmail = managers.ConfigManager.getAliceConfigByName('snipsConsoleLogin')
		self._userPassword = managers.ConfigManager.getAliceConfigByName('snipsConsolePassword')
		self._assistant = None
		self._skill = None
		self._intent = None
		self._entity = None

		self._dtSlotTypesModulesValues 		= dict()
		self._dtIntentsModulesValues		= dict()
		self._dtIntentNameSkillMatching   	= dict()

		self._mainProcessor = MainProcessor(self)
		self.initActions()
		self._loadDialogTemplateMapsInConfigManager()


	def _loadDialogTemplateMapsInConfigManager(self):
		self._dtSlotTypesModulesValues, self._dtIntentsModulesValues, self._dtIntentNameSkillMatching = self.getDialogTemplatesMaps(
			runOnAssistantId=managers.LanguageManager.activeSnipsProjectId,
			languageFilter=managers.LanguageManager.activeLanguage
		)


	@property
	def entity(self) -> Entity:
		return self._entity


	@property
	def intent(self) -> Intent:
		return self._intent


	@property
	def skill(self) -> Skill:
		return self._skill


	@property
	def assistant(self) -> Assistant:
		return self._assistant


	@property
	def userEmail(self) -> str:
		return self._userEmail


	@property
	def userId(self) -> str:
		return self._userId


	def sync(self, moduleFilter: str = None, download: bool = True) -> bool:
		self.log('[{}] Sync for module \'{}\''.format(self.name, moduleFilter or '*'))

		started = self.start()

		if not started:
			self.log('[{}] No credentials. Unable to synchronize assistant with remote console'.format(self.name))
			return False

		activeLang: str = managers.LanguageManager.activeLanguage
		activeProjectId: str = managers.LanguageManager.activeSnipsProjectId
		changes: bool = False

		try:
			changes = self.syncLocalToRemote(
				baseAssistantId=activeProjectId,
				baseLanguageFilter=activeLang,
				baseModuleFilter=moduleFilter,
				newAssistantTitle='ProjectAlice_{}'.format(managers.LanguageManager.activeLanguage)
			)

			if changes:
				if download:
					self.log('[{}] Changes detected during sync, let\'s update the assistant...'.format(self.name))
					managers.SnipsConsoleManager.doDownload()
				else:
					self.log('[{}] Changes detected during sync but not downloading yet'.format(self.name))
			else:
				self.log('[{}] No changes detected during sync'.format(self.name))

			self.stop()
		except AssistantNotFoundError:
			self.log('[{}] Assistant project id \'{}\' for lang \'{}\' doesn\'t exist. Check your config.py'.format(self.name, activeProjectId, activeLang))

		return changes


	def onStart(self):
		super().onStart()

		path = Path(commons.rootDir(), 'var/assistants', managers.LanguageManager.activeLanguage)
		if not path.exists() or not [x for x in path.iterdir() if x.is_dir()]:
			self.sync()


	def log(self, msg: str):
		if self._devMode:
			self._logger.info(msg)


	def start(self):
		if managers.SnipsConsoleManager.loginCredentialsAreConfigured():
			self.initBrowser()
			self.login(self.ROOT_URL + '/home/apps')
			return True

		return False


	def stop(self):
		self._browser.quit()


	def initActions(self):
		self._assistant = Assistant(self)
		self._skill = Skill(self)
		self._intent = Intent(self)
		self._entity = Entity(self)


	def initBrowser(self):
		options = Options()
		options.headless = True
		options.add_argument('--no-sandbox')
		options.add_argument('--disable-dev-shm-usage')
		# self._browser = webdriver.Firefox('geckodriver', options=options)
		self._browser = webdriver.Chrome('chromedriver', options=options)


	def getBrowser(self) -> WebDriver:
		return self._browser


	def reloadBrowserPage(self):
		self._browser.execute_script('location.reload()')


	def visitUrl(self, url):
		self._currentUrl = url
		self._browser.get(url)
		time.sleep(0.1)
		# self.log("[Browser] " + self._browser.title +' - ' + self._browser.current_url)


	def login(self, url: str):
		self.visitUrl(url)
		self._browser.find_element_by_class_name('cookies-analytics-info__ok-button').click()
		self._browser.find_element_by_name('email').send_keys(self._userEmail)
		self._browser.find_element_by_name('password').send_keys(self._userPassword)
		self._browser.find_element_by_css_selector('.login-page__section-public__form .button[type=submit]').click()
		self._cookie = self._browser.execute_script('return document.cookie')
		self._userId = self._browser.execute_script("return window._loggedInUser['id']")


	# TODO batch gql requests
	# payload appears to be typed wrong can be string or dict
	def postGQLBrowserly(self, payload: dict, jsonRequest: bool = True, dataReadyResponse: bool = True, rawResponse: bool = False) -> dict:
		if jsonRequest:
			payload = json.dumps(payload)
		
		payload = payload.replace("'", "__SINGLE_QUOTES__").replace("\\n", ' ')

		# self.log(payload)
		# self._browser.execute_script('console.log(\'' + payload + '\')')
		# self._browser.execute_script('console.log(\'' + payload + '\'.replace(/__SINGLE_QUOTES__/g,"\'").replace(/__QUOTES__/g,\'\\\\"\'))')

		self._browser.execute_script("document.title = 'loading'")
		self._browser.execute_script('fetch("/gql", {method: "POST", headers:{"accept":"*/*","content-type":"application/json"}, credentials: "same-origin", body:\'' + payload + '\'.replace(/__SINGLE_QUOTES__/g,"\'").replace(/__QUOTES__/g,\'\\\\"\')}).then((data) => { data.text().then((text) => { document.title = text; }); })')
		wait = WebDriverWait(self._browser, 10)
		wait.until(EC.title_contains('{'))
		response = self._browser.execute_script('return document.title')
		self._browser.execute_script("document.title = 'idle'")
		# self.log(response)

		jsonResponse = json.loads(response)

		if 'errors' in jsonResponse[0]:
			firstError = jsonResponse[0]['errors'][0]
			complexMessage = firstError['message']
			path = firstError.get('path', '')

			try:
				errorDetails = json.loads(complexMessage)
			except:
				errorDetails = {'status': 0}

			errorResponse = {
				'code': errorDetails['status'],
				'message': complexMessage,
				'context': path
			}

			raise HttpError(errorResponse['code'], errorResponse['message'], errorResponse['context'])

		if rawResponse:
			return response

		if not dataReadyResponse:
			return jsonResponse

		return jsonResponse[0]['data']


	def postGQLNatively(self, payload: dict) -> requests.Response:
		"""
		Do not use for authenticated function like MUTATIONS (and maybe certain QUERY)
		console-session is randomly present from browser (document.cookie) so we can't authenticated him automatically
		console-session cookie must be present
		"""
		url = self.ROOT_URL + '/gql'
		headers = {
			'Pragma': 'no-cache',
			'Origin': self.ROOT_URL,
			'Accept-Encoding': 'gzip, deflate, br',
			'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
			'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.80 Safari/537.36',
			'content-type': 'application/json',
			'accept': '*/*',
			'Cache-Control': 'no-cache',
			'Referer': self.ROOT_URL + '/home/assistants',
			'Cookie': self._cookie,
			'Connection': 'keep-alive'
		}
		return requests.post(url=url, data=payload, headers=headers)


	# noinspection PyUnusedLocal
	def findRunnableAssistant(self, assistantId: str, assistantLanguage: str, newAssistantTitle: str = '', persistLocal: bool = False) -> str:
		if not newAssistantTitle: newAssistantTitle = 'ProjectAlice_{}'.format(managers.LanguageManager.activeLanguage)

		runOnAssistantId = None

		# AssistantId provided
		if assistantId:
			if not self._assistant.exists(assistantId):
				# If not found remotely, stop everything
				raise AssistantNotFoundError(4001, 'Assistant with id {} not found'.format(assistantId), ['assistant'])
			# If found remotely, just use it
			runOnAssistantId = assistantId
			self.log('Using provided assistantId: {}'.format(runOnAssistantId))


		if not runOnAssistantId:
			# Try to find the first local assistant for the targeted language
			localFirstAssistantId = self._mainProcessor.getLocalFirstAssistantByLanguage(assistantLanguage=assistantLanguage, returnId=True)

			if not localFirstAssistantId or not self._assistant.exists(localFirstAssistantId):
				# If not found remotely, create a new one
				runOnAssistantId = self._assistant.create(title=newAssistantTitle, language=assistantLanguage)
				self.log('Using new assistantId: {}'.format(runOnAssistantId))
			else:
				# If found remotely, just use it
				runOnAssistantId = localFirstAssistantId
				self.log('Using first local assistantId: {}'.format(runOnAssistantId))

		# Add assistant in cache locally if it isn't the case
		self._mainProcessor.syncRemoteToLocalAssistant(
			assistantId=runOnAssistantId,
			assistantLanguage=assistantLanguage,
			assistantTitle=self._assistant.getTitleById(runOnAssistantId)
		)

		return runOnAssistantId


	def syncLocalToRemote(self, baseAssistantId: str, baseModuleFilter: str, newAssistantTitle: str = '', baseLanguageFilter: str = 'en') -> bool:
		# RemoteFetch/LocalCheck/CreateIfNeeded: assistant

		runOnAssistantId = self.findRunnableAssistant(
			assistantId=baseAssistantId,
			assistantLanguage=baseLanguageFilter,
			newAssistantTitle=newAssistantTitle,
			persistLocal=True
		)

		if managers.LanguageManager.activeSnipsProjectId != runOnAssistantId:
			managers.LanguageManager.changeActiveSnipsProjectIdForLanguage(runOnAssistantId, baseLanguageFilter)

		# From module intents files to dict then push to SnipsConsole
		return self._mainProcessor.syncLocalToRemote(runOnAssistantId, moduleFilter=baseModuleFilter, languageFilter=baseLanguageFilter)


	def syncRemoteToLocal(self, baseAssistantId: str, baseModuleFilter: str, baseLanguageFilter: str = 'en'):
		# RemoteFetch/LocalCheck/CreateIfNeeded: assistant
		runOnAssistantId = self.findRunnableAssistant(
			assistantId=baseAssistantId,
			assistantLanguage=baseLanguageFilter,
			persistLocal=False
		)

		# From SnipsConsole objects to module intents files
		self._mainProcessor.syncRemoteToLocal(runOnAssistantId, languageFilter=baseLanguageFilter, moduleFilter=baseModuleFilter)


	def getDialogTemplatesMaps(self, runOnAssistantId: str, languageFilter: str, moduleFilter: str = None) -> tuple:
		return self._mainProcessor.buildMapsFromDialogTemplates(runOnAssistantId, languageFilter=languageFilter, moduleFilter=moduleFilter)


	def getIntentsByModuleName(self, runOnAssistantId: str, languageFilter: str, moduleFilter: str = None) -> list:
		slotTypesModulesValues, intentsModulesValues, intentNameSkillMatching = self.getDialogTemplatesMaps(
			runOnAssistantId=runOnAssistantId,
			languageFilter=languageFilter
		)

		intents = list()

		for dtIntentName, dtModuleName in intentNameSkillMatching.items():
			if dtModuleName == moduleFilter:
				intents.append({
					'name': dtIntentName,
					'description': intentsModulesValues[dtIntentName]['__otherattributes__']['description']
				})

		return intents


	def getUtterancesByIntentName(self, runOnAssistantId: str, languageFilter: str, intentFilter: str = None) -> list:
		slotTypesModulesValues, intentsModulesValues, intentNameSkillMatching = self.getDialogTemplatesMaps(
			runOnAssistantId=runOnAssistantId,
			languageFilter=languageFilter
		)

		utterances = list()
		
		for dtIntentName, dtModuleName in intentNameSkillMatching.items():
			if dtIntentName == intentFilter:
				for utterance in intentsModulesValues[dtIntentName]['utterances'].items():
					utterances.append({
						'sentence': utterance
					})

		return utterances


	@property
	def dtSlotTypesModulesValues(self) -> dict:
		return self._dtSlotTypesModulesValues


	@property
	def dtIntentsModulesValues(self) -> dict:
		return self._dtIntentsModulesValues


	@property
	def dtIntentNameSkillMatching(self) -> dict:
		return self._dtIntentNameSkillMatching
