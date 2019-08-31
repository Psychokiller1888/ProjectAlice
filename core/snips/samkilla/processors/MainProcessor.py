# -*- coding: utf-8 -*-

import json

import os
from os import listdir

from core.snips.samkilla.exceptions.HttpError import HttpError
from core.snips.samkilla.models.EnumSkillImageUrl import EnumSkillImageUrl as EnumSkillImageUrlClass
from core.snips.samkilla.models.util import skillNameToCamelCase
from core.snips.samkilla.processors.IntentRemoteProcessor import IntentRemoteProcessor
from core.snips.samkilla.processors.ModuleRemoteProcessor import ModuleRemoteProcessor
from core.snips.samkilla.processors.SlotTypeRemoteProcessor import SlotTypeRemoteProcessor

EnumSkillImageUrl = EnumSkillImageUrlClass()

class MainProcessor():

	SAVED_ASSISTANTS_DIR = os.path.join('var', 'assistants')
	SAVED_MODULES_DIR = 'modules'

	def __init__(self, ctx):
		self._ctx = ctx
		self._modules = dict()
		self._savedAssistants = dict()
		self._savedSlots = dict()
		self._savedIntents = dict()
		self.initSavedAssistants()
		self.initSavedSlots()
		self.initSavedIntents()


	def initSavedIntents(self):
		for lang in listdir(self.SAVED_ASSISTANTS_DIR):
			if lang.startswith('.'): continue

			self._savedIntents[lang] = dict()
			insideLangDir = os.path.join(self.SAVED_ASSISTANTS_DIR, lang)
			os.makedirs(insideLangDir, exist_ok=True)
			self._savedIntents[lang] = dict()

			for projectId in listdir(insideLangDir):
				insideProjectSlotDir = os.path.join(insideLangDir, projectId, 'intents')
				os.makedirs(insideProjectSlotDir, exist_ok=True)
				self._savedIntents[lang][projectId] = dict()

				for intent in listdir(insideProjectSlotDir):
					intentFilePathName = os.path.join(insideProjectSlotDir, intent)

					with open(intentFilePathName) as intentFilePathNameHandler:
						wholeIntentDefinition = json.load(intentFilePathNameHandler)
						self._savedIntents[lang][projectId][wholeIntentDefinition['name']] = wholeIntentDefinition


	def initSavedSlots(self):
		for lang in listdir(self.SAVED_ASSISTANTS_DIR):
			if lang.startswith('.'): continue

			self._savedSlots[lang] = dict()
			insideLangDir = os.path.join(self.SAVED_ASSISTANTS_DIR, lang)
			os.makedirs(insideLangDir, exist_ok=True)
			self._savedSlots[lang] = dict()

			for projectId in listdir(insideLangDir):
				insideProjectSlotDir = os.path.join(insideLangDir, projectId, 'slots')
				os.makedirs(insideProjectSlotDir, exist_ok=True)
				self._savedSlots[lang][projectId] = dict()

				for slot in listdir(insideProjectSlotDir):
					slotFilePathName = os.path.join(insideProjectSlotDir, slot)

					with open(slotFilePathName) as slotFilePathNameHandler:
						wholeSlotDefinition = json.load(slotFilePathNameHandler)
						self._savedSlots[lang][projectId][wholeSlotDefinition['name']] = wholeSlotDefinition

	def initSavedAssistants(self):
		os.makedirs(self.SAVED_ASSISTANTS_DIR, exist_ok=True)

		for lang in listdir(self.SAVED_ASSISTANTS_DIR):
			if lang.startswith('.'): continue

			insideLangDir = os.path.join(self.SAVED_ASSISTANTS_DIR, lang)
			os.makedirs(insideLangDir, exist_ok=True)
			self._savedAssistants[lang] = dict()

			for projectId in listdir(insideLangDir):
				projectIdFilePathName = os.path.join(insideLangDir, projectId, '_assistant.json')
				self._savedAssistants[lang][projectId] = dict()

				with open(projectIdFilePathName) as projectIdFileHandler:
					wholeAssistant = json.load(projectIdFileHandler)
					self._savedAssistants[lang][projectId] = wholeAssistant
					self.safeBaseDicts(projectId, lang)

	def hasLocalAssistantByIdAndLanguage(self, assistantLanguage, assistantId):
		return assistantLanguage in self._savedAssistants and assistantId in self._savedAssistants[assistantLanguage]

	def getLocalFirstAssistantByLanguage(self, assistantLanguage, returnId=False):
		if assistantLanguage in self._savedAssistants:
			assistantKeysForLanguage = list(self._savedAssistants[assistantLanguage].keys())

			if len(assistantKeysForLanguage) > 0:
				if returnId:
					return self._savedAssistants[assistantLanguage][assistantKeysForLanguage[0]]['id']

				return self._savedAssistants[assistantLanguage][assistantKeysForLanguage[0]]

		return None


	def safeBaseDicts(self, assistantId, assistantLanguage):
		baseDicts = ['modules', 'slotTypes', 'intents']

		for baseDict in baseDicts:
			self._savedAssistants[assistantLanguage][assistantId].setdefault(baseDict, dict())

	def persistToLocalAssistantCache(self, assistantId, assistantLanguage):
		assistantMountpoint = os.path.join(self.SAVED_ASSISTANTS_DIR, assistantLanguage, assistantId)
		os.makedirs(assistantMountpoint, exist_ok=True)

		self.safeBaseDicts(assistantId, assistantLanguage)

		state = self._savedAssistants[assistantLanguage][assistantId]

		with open(os.path.join(assistantMountpoint, 'assistant.json'), 'w') as projectIdFileHandler:
			json.dump(state, projectIdFileHandler, indent=4, sort_keys=False, ensure_ascii=False)
			# self._ctx.log('\n[Persist] local assistant {} in {}'.format(assistantId, assistantLanguage))

	def syncRemoteToLocalAssistant(self, assistantId, assistantLanguage, assistantTitle):
		if not self.hasLocalAssistantByIdAndLanguage(assistantId=assistantId, assistantLanguage=assistantLanguage):
			newState = {
				'id': assistantId,
				'name': assistantTitle,
				'language': assistantLanguage,
				'modules': dict(),
				'slotTypes': dict(),
				'intents': dict()
			}

			if not assistantLanguage in self._savedAssistants:
				self._savedAssistants[assistantLanguage] = dict()

			self._savedAssistants[assistantLanguage][assistantId] = newState
			self.persistToLocalAssistantCache(assistantId=assistantId, assistantLanguage=assistantLanguage)
			self.initSavedSlots()
			self.initSavedIntents()

	def syncRemoteToLocalModuleCache(self, assistantId, assistantLanguage, moduleName, syncState, persist=False):
		self._savedAssistants[assistantLanguage][assistantId]['modules'][moduleName] = syncState

		if persist:
			self.persistToLocalAssistantCache(assistantId=assistantId, assistantLanguage=assistantLanguage)

	def syncRemoteToLocalSlotTypeCache(self, assistantId, assistantLanguage, slotTypeName, syncState, persist=False):
		self._savedAssistants[assistantLanguage][assistantId]['slotTypes'][slotTypeName] = syncState

		if persist:
			self.persistToLocalAssistantCache(assistantId=assistantId, assistantLanguage=assistantLanguage)

	def syncRemoteToLocalIntentCache(self, assistantId, assistantLanguage, intentName, syncState, persist=False):
		self._savedAssistants[assistantLanguage][assistantId]['intents'][intentName] = syncState

		if persist:
			self.persistToLocalAssistantCache(assistantId=assistantId, assistantLanguage=assistantLanguage)

	def getModuleFromFile(self, moduleFile, moduleLanguage):
		with open(moduleFile) as f:
			module = json.load(f)
			module['language'] = moduleLanguage

			if module['module'] not in self._modules:
				self._ctx.log('\n[Inconsistent] Module {} has a name different from its directory'.format(module['module']))
				return None

			self._modules[module['module']][moduleLanguage] = module
			self._ctx.log('[FilePull] Loading module {}'.format(module['module']))
			return module

	def getModuleSyncStateByLanguageAndAssistantId(self, moduleName, language, assistantId):
		moduleSyncState = None

		if language in self._savedAssistants and \
				assistantId in self._savedAssistants[language] and \
				moduleName in self._savedAssistants[language][assistantId]['modules']:
			moduleSyncState = self._savedAssistants[language][assistantId]['modules'][moduleName]

		return moduleSyncState

	def getSlotTypeSyncStateByLanguageAndAssistantId(self, slotTypeName, language, assistantId):
		slotSyncState = None

		if language in self._savedAssistants and \
				assistantId in self._savedAssistants[language] and \
				slotTypeName in self._savedAssistants[language][assistantId]['slotTypes']:
			slotSyncState = self._savedAssistants[language][assistantId]['slotTypes'][slotTypeName]

		return slotSyncState

	def getIntentSyncStateByLanguageAndAssistantId(self, intentName, language, assistantId):
		intentSyncState = None

		if language in self._savedAssistants and \
				assistantId in self._savedAssistants[language] and \
				intentName in self._savedAssistants[language][assistantId]['intents']:
			intentSyncState = self._savedAssistants[language][assistantId]['intents'][intentName]

		return intentSyncState

	def persistToGlobalAssistantSlots(self, assistantId, assistantLanguage, slotNameFilter=None):
		assistantSlotsMountpoint = os.path.join(self.SAVED_ASSISTANTS_DIR, assistantLanguage, assistantId, 'slots')
		os.makedirs(assistantSlotsMountpoint, exist_ok=True)

		slotTypes = self._savedSlots[assistantLanguage][assistantId]

		for slotTypeName in slotTypes.keys():
			slotType = slotTypes[slotTypeName]

			if slotNameFilter and slotNameFilter != slotTypeName: continue

			with open(os.path.join(assistantSlotsMountpoint, '{}.json'.format(slotTypeName)), 'w') as slotTypeFileHandler:
				json.dump(slotType, slotTypeFileHandler, indent=4, sort_keys=False, ensure_ascii=False)
				# self._ctx.log('[Persist] global slot {}'.format(slotTypeName))


	def persistToGlobalAssistantIntents(self, assistantId, assistantLanguage, intentNameFilter=None):
		assistantIntentsMountpoint = os.path.join(self.SAVED_ASSISTANTS_DIR, assistantLanguage, assistantId, 'intents')
		os.makedirs(assistantIntentsMountpoint, exist_ok=True)

		intents = self._savedIntents[assistantLanguage][assistantId]

		for intentName in intents.keys():
			intent = intents[intentName]

			if intentNameFilter and intentNameFilter != intentName: continue

			with open(os.path.join(assistantIntentsMountpoint, '{}.json'.format(intentName)), 'w') as slotTypeFileHandler:
				json.dump(intent, slotTypeFileHandler, indent=4, sort_keys=False, ensure_ascii=False)
				# self._ctx.log('[Persist] global intent {}'.format(intentName))


	def syncGlobalSlotType(self, assistantId, assistantLanguage, slotTypeName, slotDefinition, persist=False):
		self._savedSlots[assistantLanguage][assistantId][slotTypeName] = slotDefinition

		if persist:
			self.persistToGlobalAssistantSlots(assistantId=assistantId, assistantLanguage=assistantLanguage, slotNameFilter=slotTypeName)


	def syncGlobalIntent(self, assistantId, assistantLanguage, intentName, intentDefinition, persist=False):
		self._savedIntents[assistantLanguage][assistantId][intentName] = intentDefinition

		if persist:
			self.persistToGlobalAssistantIntents(assistantId=assistantId, assistantLanguage=assistantLanguage, intentNameFilter=intentName)


	def mergeModuleSlotTypes(self, slotTypesModulesValues, assistantId, slotLanguage=None):
		mergedSlotTypes = dict()
		slotTypesGlobalValues = dict()

		keys = slotTypesModulesValues.keys()

		for slotName in keys:
			if slotName in self._savedSlots[slotLanguage][assistantId]:
				savedSlotType = self._savedSlots[slotLanguage][assistantId][slotName]

				slotTypesGlobalValues[savedSlotType['name']] = {'__otherattributes__': {
					'name': savedSlotType['name'],
					'matchingStrictness': savedSlotType['matchingStrictness'],
					'automaticallyExtensible': savedSlotType['automaticallyExtensible'],
					'useSynonyms': savedSlotType['useSynonyms'],
					'values': list()
				}}

				for savedSlotValue in savedSlotType['values']:
					if savedSlotValue['value'] not in slotTypesGlobalValues[savedSlotType['name']]:
						slotTypesGlobalValues[savedSlotType['name']][savedSlotValue['value']] = dict()

						if 'synonyms' in savedSlotValue:
							for synonym in savedSlotValue['synonyms']:
								if len(synonym) == 0: continue
								slotTypesGlobalValues[savedSlotType['name']][savedSlotValue['value']].setdefault(synonym, True)

		for slotName in slotTypesModulesValues.keys():

			slotTypeCatalogValues = slotTypesGlobalValues if slotName in slotTypesGlobalValues else slotTypesModulesValues

			mergedSlotTypes[slotName] = slotTypeCatalogValues[slotName]['__otherattributes__']
			mergedSlotTypes[slotName]['values'] = list()

			for slotValue in slotTypeCatalogValues[slotName].keys():
				if slotValue == '__otherattributes__': continue
				synonyms = list()

				for synonym in slotTypeCatalogValues[slotName][slotValue].keys():
					synonyms.append(synonym)

				mergedSlotTypes[slotName]['values'].append({'value': slotValue, 'synonyms': synonyms})

			self.syncGlobalSlotType(
				assistantId=assistantId,
				assistantLanguage=slotLanguage,
				slotTypeName=slotName,
				slotDefinition=mergedSlotTypes[slotName],
				persist=True
			)

		return mergedSlotTypes



	def mergeModuleIntents(self, intentsModulesValues, assistantId, intentLanguage=None):
		mergedIntents = dict()
		intentsGlobalValues = dict()

		keys = intentsModulesValues.keys()

		for intentName in keys:
			if intentName in self._savedIntents[intentLanguage][assistantId]:
				savedIntent = self._savedIntents[intentLanguage][assistantId][intentName]

				intentsGlobalValues[savedIntent['name']] = {'__otherattributes__': {
					'name': savedIntent['name'],
					'description': savedIntent['description'],
					'enabledByDefault': savedIntent['enabledByDefault'],
					'utterances': list(),
					'slots': list()
				},
					'utterances': dict(),
					'slots': dict()
				}

				for savedUtterance in savedIntent['utterances']:
					intentsGlobalValues[savedIntent['name']]['utterances'].setdefault(savedUtterance, True)

				for moduleSlot in savedIntent['slots']:
					intentsGlobalValues[savedIntent['name']]['slots'].setdefault(moduleSlot['name'], moduleSlot)


		for intentName in intentsModulesValues.keys():

			intentCatalogValues = intentsGlobalValues if intentName in intentsGlobalValues else intentsModulesValues

			mergedIntents[intentName] = intentCatalogValues[intentName]['__otherattributes__']
			mergedIntents[intentName]['utterances'] = list()
			mergedIntents[intentName]['slots'] = list()

			for intentUtteranceValue in intentCatalogValues[intentName]['utterances'].keys():
				mergedIntents[intentName]['utterances'].append(intentUtteranceValue)

			for intentSlotNameValue in intentCatalogValues[intentName]['slots'].keys():
				mergedIntents[intentName]['slots'].append(intentCatalogValues[intentName]['slots'][intentSlotNameValue])

			self.syncGlobalIntent(
				assistantId=assistantId,
				assistantLanguage=intentLanguage,
				intentName=intentName,
				intentDefinition=mergedIntents[intentName],
				persist=True
			)

		return mergedIntents


	def buildMapsFromDialogTemplates(self, runOnAssistantId, moduleFilter=None, languageFilter=None):
		self._modules = dict()

		rootDir = 'modules'
		os.makedirs(rootDir, exist_ok=True)

		slotTypesModulesValues = dict()
		intentsModulesValues = dict()
		intentNameSkillMatching = dict()

		for dir in listdir(rootDir):
			intentsPath = os.path.join(rootDir, dir, 'dialogTemplate')

			if not os.path.isdir(intentsPath):
				continue

			moduleName = dir
			self._modules[moduleName] = dict()

			for languageFile in listdir(intentsPath):
				moduleFile = os.path.join(intentsPath, languageFile)
				moduleLanguage = os.path.basename(moduleFile).replace('.json', '')
				if languageFilter and languageFilter != moduleLanguage: continue
				module = self.getModuleFromFile(moduleFile=moduleFile, moduleLanguage=moduleLanguage)
				if not module: continue

				# We need all slotTypes values of all modules, even if there is a module filter
				for moduleSlotType in module['slotTypes']:
					if moduleSlotType['name'] not in slotTypesModulesValues:
						slotTypesModulesValues[moduleSlotType['name']] = {'__otherattributes__': {
							'name': moduleSlotType['name'],
							'matchingStrictness': moduleSlotType['matchingStrictness'],
							'automaticallyExtensible': moduleSlotType['automaticallyExtensible'],
							'useSynonyms': moduleSlotType['useSynonyms'],
							'values': list()
						}}

					for moduleSlotValue in moduleSlotType['values']:
						if moduleSlotValue['value'] not in slotTypesModulesValues[moduleSlotType['name']]:
							slotTypesModulesValues[moduleSlotType['name']][moduleSlotValue['value']] = dict()

							if 'synonyms' in moduleSlotValue:
								for synonym in moduleSlotValue['synonyms']:
									if len(synonym) == 0: continue
									if synonym not in slotTypesModulesValues[moduleSlotType['name']][
										moduleSlotValue['value']]:
										slotTypesModulesValues[moduleSlotType['name']][moduleSlotValue['value']][
											synonym] = True

				# We need all intents values of all modules, even if there is a module filter
				for moduleIntent in module['intents']:
					if moduleIntent['name'] not in intentsModulesValues:
						intentNameSkillMatching[moduleIntent['name']] = moduleName

						intentsModulesValues[moduleIntent['name']] = {'__otherattributes__': {
							'name': moduleIntent['name'],
							'description': moduleIntent['description'],
							'enabledByDefault': moduleIntent['enabledByDefault'],
							'utterances': list(),
							'slots': list()
						},
							'utterances': dict(),
							'slots': dict()
						}

					if 'utterances' in moduleIntent:
						for moduleUtterance in moduleIntent['utterances']:
							intentsModulesValues[moduleIntent['name']]['utterances'].setdefault(moduleUtterance, True)

					if 'slots' in moduleIntent:
						for moduleSlot in moduleIntent['slots']:
							intentsModulesValues[moduleIntent['name']]['slots'].setdefault(moduleSlot['name'], moduleSlot)

				if moduleFilter and moduleFilter != moduleName:
					del self._modules[moduleName]
					continue

		return slotTypesModulesValues, intentsModulesValues, intentNameSkillMatching

	# TODO to refacto in different method of a new Processor
	def syncLocalToRemote(self, runOnAssistantId, moduleFilter=None, languageFilter=None):

		slotTypesModulesValues, intentsModulesValues, intentNameSkillMatching = self.buildMapsFromDialogTemplates(
			runOnAssistantId=runOnAssistantId,
			moduleFilter=moduleFilter,
			languageFilter=languageFilter
		)

		# Get a dict with all slotTypes
		typeEntityMatching, globalChangesSlotTypes = self.syncLocalToRemoteSlotTypes(
			slotTypesModulesValues,
			runOnAssistantId,
			languageFilter,
			moduleFilter
		)

		skillNameIdMatching, globalChangesModules = self.syncLocalToRemoteModules(
			typeEntityMatching,
			runOnAssistantId,
			languageFilter,
			moduleFilter
		)

		globalChangesIntents = self.syncLocalToRemoteIntents(
			skillNameIdMatching,
			intentNameSkillMatching,
			typeEntityMatching,
			intentsModulesValues,
			runOnAssistantId,
			languageFilter,
			moduleFilter
		)

		return globalChangesSlotTypes or globalChangesModules or globalChangesIntents


	def syncLocalToRemoteSlotTypes(self, slotTypesModulesValues, runOnAssistantId, languageFilter=None, moduleFilter=None):
		slotTypesSynced = dict()
		globalChanges = False

		mergedSlotTypes = self.mergeModuleSlotTypes(
			slotTypesModulesValues=slotTypesModulesValues,
			assistantId=runOnAssistantId,
			slotLanguage=languageFilter
		)

		typeEntityMatching = dict()

		for slotName in mergedSlotTypes.keys():
			slotType = mergedSlotTypes[slotName]

			slotSyncState = self.getSlotTypeSyncStateByLanguageAndAssistantId(
				slotTypeName=slotName,
				language=languageFilter,
				assistantId=runOnAssistantId
			)

			slotRemoteProcessor = SlotTypeRemoteProcessor(
				ctx=self._ctx,
				slotType=slotType,
				slotLanguage=languageFilter,
				assistantId=runOnAssistantId,
			)

			newSlotTypeSyncState, changes = slotRemoteProcessor.syncSlotTypesOnAssistantSafely(
				slotTypeSyncState=slotSyncState,
				hashComputationOnly=False
			)

			if changes: globalChanges = True

			typeEntityMatching[slotName] = newSlotTypeSyncState

			self.syncRemoteToLocalSlotTypeCache(
				assistantId=runOnAssistantId,
				assistantLanguage=languageFilter,
				slotTypeName=slotName,
				syncState=newSlotTypeSyncState,
				persist=True
			)

			slotTypesSynced[slotName] = True

		# Remove deprecated/renamed slotTypes
		hasDeprecatedSlotTypes = list()

		for slotTypeName in self._savedAssistants[languageFilter][runOnAssistantId]['slotTypes'].keys():
			if slotTypeName not in slotTypesSynced:
				self._ctx.log('[Deprecated] SlotType {}'.format(slotTypeName))
				slotTypeCacheData = self._savedAssistants[languageFilter][runOnAssistantId]['slotTypes'][slotTypeName]

				entityId = slotTypeCacheData['entityId']
				self._ctx.Entity.delete(entityId=entityId, language=languageFilter)

				hasDeprecatedSlotTypes.append(slotTypeName)

		if len(hasDeprecatedSlotTypes) > 0:
			globalChanges = True

			for slotTypeName in hasDeprecatedSlotTypes:
				del self._savedAssistants[languageFilter][runOnAssistantId]['slotTypes'][slotTypeName]

				if slotTypeName in self._savedSlots[languageFilter][runOnAssistantId]:
					del self._savedSlots[languageFilter][runOnAssistantId][slotTypeName]

					globalSlotTypeFile = os.path.join(self.SAVED_ASSISTANTS_DIR, languageFilter, runOnAssistantId, 'slots', '{}.json'.format(slotTypeName))

					if os.path.isfile(globalSlotTypeFile):
						os.unlink(globalSlotTypeFile)

			self.persistToLocalAssistantCache(assistantId=runOnAssistantId, assistantLanguage=languageFilter)

		return typeEntityMatching, globalChanges



	def syncLocalToRemoteIntents(self, skillNameIdMatching, intentNameSkillMatching, typeEntityMatching,
								 intentsModulesValues, runOnAssistantId, languageFilter=None, moduleFilter=None):

		intentsSynced = dict()
		globalChanges = False

		mergedIntents = self.mergeModuleIntents(
			intentsModulesValues=intentsModulesValues,
			assistantId=runOnAssistantId,
			intentLanguage=languageFilter
		)

		for intentName in mergedIntents.keys():
			intent = mergedIntents[intentName]

			intentSyncState = self.getIntentSyncStateByLanguageAndAssistantId(
				intentName=intentName,
				language=languageFilter,
				assistantId=runOnAssistantId
			)

			intentRemoteProcessor = IntentRemoteProcessor(
				ctx=self._ctx,
				intent=intent,
				intentLanguage=languageFilter,
				assistantId=runOnAssistantId,
			)

			if intentName not in intentNameSkillMatching or intentNameSkillMatching[intentName] not in skillNameIdMatching:
				intentsSynced[intentName] = True
				continue

			skillId = skillNameIdMatching[intentNameSkillMatching[intentName]]

			newIntentSyncState, changes = intentRemoteProcessor.syncIntentsOnAssistantSafely(
				typeEntityMatching=typeEntityMatching,
				skillId=skillId,
				intentSyncState=intentSyncState,
				hashComputationOnly=False
			)

			if changes: globalChanges = True

			self.syncRemoteToLocalIntentCache(
				assistantId=runOnAssistantId,
				assistantLanguage=languageFilter,
				intentName=intentName,
				syncState=newIntentSyncState,
				persist=True
			)

			intentsSynced[intentName] = True

		# Remove deprecated/renamed slotTypes
		hasDeprecatedIntents = list()

		for intentName in self._savedAssistants[languageFilter][runOnAssistantId]['intents'].keys():
			if intentName not in intentsSynced:
				self._ctx.log('[Deprecated] Intent {}'.format(intentName))
				intentCacheData = self._savedAssistants[languageFilter][runOnAssistantId]['intents'][intentName]

				intentId = intentCacheData['intentId']

				try:
					self._ctx.Intent.delete(intentId=intentId)

				except HttpError as he:
					isAttachToSkillIds = (json.loads(json.loads(he.message)['message'])['skillIds'])

					for isAttachToSkillId in isAttachToSkillIds:
						self._ctx.Intent.removeFromSkill(intentId=intentId, skillId=isAttachToSkillId, userId=self._ctx._userId, deleteAfter=False)

					self._ctx.Intent.delete(intentId=intentId)

				hasDeprecatedIntents.append(intentName)

		if len(hasDeprecatedIntents) > 0:
			globalChanges = True

			for intentName in hasDeprecatedIntents:
				del self._savedAssistants[languageFilter][runOnAssistantId]['intents'][intentName]

				if intentName in self._savedIntents[languageFilter][runOnAssistantId]:
					del self._savedIntents[languageFilter][runOnAssistantId][intentName]

					globalIntentFile = os.path.join(self.SAVED_ASSISTANTS_DIR, languageFilter, runOnAssistantId, 'intents', '{}.json'.format(intentName))

					if os.path.isfile(globalIntentFile):
						os.unlink(globalIntentFile)

			self.persistToLocalAssistantCache(assistantId=runOnAssistantId, assistantLanguage=languageFilter)

		return globalChanges


	def syncLocalToRemoteModules(self, typeEntityMatching, runOnAssistantId, languageFilter=None, moduleFilter=None):
		modulesSynced = dict()
		globalChanges = False

		skillNameIdMatching = dict()

		for moduleName in self._modules.keys():
			if languageFilter not in self._modules[moduleName]:
				continue

			module = self._modules[moduleName][languageFilter]

			moduleSyncState = self.getModuleSyncStateByLanguageAndAssistantId(
				moduleName=moduleName,
				language=languageFilter,
				assistantId=runOnAssistantId
			)

			# Start a ModuleRemoteProcessor tasker for each module(a.k.a module)
			moduleRemoteProcessor = ModuleRemoteProcessor(
				ctx=self._ctx,
				assistantId=runOnAssistantId,
				module=module,
				moduleName=moduleName,
				moduleLanguage=languageFilter
			)

			newModuleSyncState, changes = moduleRemoteProcessor.syncModulesOnAssistantSafely(
				typeEntityMatching=typeEntityMatching,
				moduleSyncState=moduleSyncState,
				hashComputationOnly=False
			)

			if changes: globalChanges = True

			skillNameIdMatching[moduleName] = newModuleSyncState['skillId']

			self.syncRemoteToLocalModuleCache(
				assistantId=runOnAssistantId,
				assistantLanguage=languageFilter,
				moduleName=moduleName,
				syncState=newModuleSyncState,
				persist=True
			)

			modulesSynced[moduleName] = True

		# Remove deprecated/renamed modules
		hasDeprecatedModules = list()

		for moduleName in self._savedAssistants[languageFilter][runOnAssistantId]['modules'].keys():
			if moduleFilter and moduleName != moduleFilter:
				continue

			if moduleName not in modulesSynced:
				self._ctx.log('[Deprecated] Module {}'.format(moduleName))
				moduleCacheData = self._savedAssistants[languageFilter][runOnAssistantId]['modules'][moduleName]
				skillId = moduleCacheData['skillId']
				slotTypeKeys = moduleCacheData['slotTypes'].keys() if 'slotTypes' in moduleCacheData else list()
				intentKeys = moduleCacheData['intents'].keys() if 'intents' in moduleCacheData else list()

				for slotTypeName in slotTypeKeys:
					entityId = moduleCacheData['slotTypes'][slotTypeName]['entityId']
					self._ctx.Entity.delete(entityId=entityId, language=languageFilter)

				for intentName in intentKeys:
					intentId = moduleCacheData['intents'][intentName]['intentId']
					self._ctx.Intent.removeFromSkill(userId=self._ctx._userId, skillId=skillId, intentId=intentId, deleteAfter=True)

				self._ctx.Skill.removeFromAssistant(assistantId=runOnAssistantId, skillId=skillId, deleteAfter=True)

				hasDeprecatedModules.append(moduleName)

		if len(hasDeprecatedModules) > 0:
			globalChanges = True

			for moduleName in hasDeprecatedModules:
				del self._savedAssistants[languageFilter][runOnAssistantId]['modules'][moduleName]

			self.persistToLocalAssistantCache(assistantId=runOnAssistantId, assistantLanguage=languageFilter)

		return skillNameIdMatching, globalChanges


	# TODO to refacto in different method of a new Processor
	def syncRemoteToLocal(self, runOnAssistantId, moduleFilter=None, languageFilter=None):

		# Build cache
		remoteIndexedEntities = self._ctx.Entity.listEntitiesByUserEmail(userEmail=self._ctx._userEmail, returnAllCacheIndexedBy='id')
		remoteIndexedIntents = self._ctx.Intent.listIntentsByUserId(userId=self._ctx._userId, returnAllCacheIndexedBy='id')
		remoteIndexedSkills = self._ctx.Skill.listSkillsByUserId(userId=self._ctx._userId, returnAllCacheIndexedBy='id')
		hasFork = False

		# Check for fork and execute fork if needed
		for assistant in self._ctx.Assistant.list(rawResponse=True)['assistants']:
			if assistant['id'] != runOnAssistantId:
				continue

			for skill in assistant['skills']:
				skillId = skill['id']

				if skillId not in remoteIndexedSkills:
					skillId = self._ctx.Assistant.forkAssistantSkill(assistantId=runOnAssistantId, sourceSkillId=skillId)
					self._ctx.log('[Forked] Skill from {} to {}'.format(skill['id'], skillId))
					hasFork = True

				for intent in skill['intents']:
					intentId = intent['id']

					if intentId not in remoteIndexedIntents:
						intentId = self._ctx.Skill.forkSkillIntent(skillId=skillId, sourceIntentId=intentId, userId=self._ctx._userId)
						self._ctx.log('[Forked] Intent from {} to {} used in skill {}'.format(intent['id'], intentId, skillId))
						hasFork = True

		if hasFork:
			# Rebuild cache
			self._ctx.Entity.listEntitiesByUserEmail(userEmail=self._ctx._userEmail)
			self._ctx.Intent.listIntentsByUserId(userId=self._ctx._userId)
			self._ctx.Skill.listSkillsByUserId(userId=self._ctx._userId)

		# Build each module configuration
		modules = dict()

		cachedIndexedSkills = self._ctx.Skill.listSkillsByUserIdAndAssistantId(userId=self._ctx._userId, assistantId=runOnAssistantId, fromCache=True)

		for skill in cachedIndexedSkills:
			moduleName = skillNameToCamelCase(skill['name'])

			if moduleFilter and moduleName != moduleFilter:
				continue

			modules[moduleName] = {
			  	'module': moduleName,
				'icon': EnumSkillImageUrl.urlToResourceKey(skill['imageUrl']),
				'description': skill['description'],
				'slotTypes': list(),
				'intents': list()
			}
			moduleSyncState = {
				'skillId': skill['id'],
				'name': moduleName,
				'slotTypes': dict(),
				'intents': dict(),
				'hash': ''
			}

			cachedIndexedIntents = self._ctx.Intent.listIntentsByUserIdAndSkillId(userId=self._ctx._userId, skillId=skill['id'], fromCache=True)
			typeEntityMatching = dict()

			for intent in cachedIndexedIntents:
				intentName = intent['name']

				if intentName.startswith(skill['name']+'_'):
					intentName = intentName.replace(skill['name']+'_', '')

				intentName = skillNameToCamelCase(intentName)

				utterances = list()
				slots = list()
				slotIdAndNameMatching = dict()
				objectUtterances = self._ctx.Intent.listUtterancesByIntentId(intentId=intent['id'])

				for slot in intent['slots']:
					slotIdAndNameMatching[slot['id']] = slot

				for objectUtterance in objectUtterances:
					text = objectUtterance['text']
					positionOffset = 0

					for hole in objectUtterance['data']:
						word = hole['text']
						start = hole['range']['start'] + positionOffset
						end = hole['range']['end'] + positionOffset
						slotName = slotIdAndNameMatching[hole['slotId']]['name']
						slotName = skillNameToCamelCase(slotName)
						newWord = '{' + word + self._ctx.Intent.GLUE_SLOT_WORD + slotName + '}'
						text = text[:start] + newWord + text[end:]
						positionOffset += len(newWord) - len(word)

					utterances.append(text)

				cachedIndexedEntities =  self._ctx.Entity.listEntitiesByUserEmailAndIntentId(userEmail=self._ctx._userEmail, intentId=intent['id'], fromCache=True)

				for entity in cachedIndexedEntities:
					if entity['id'] in typeEntityMatching:
						continue

					values = self._ctx.Entity.listEntityValuesByEntityId(entityId=entity['id'])
					entityName = skillNameToCamelCase(entity['name'])
					typeEntityMatching[entity['id']] = entityName

					modules[moduleName]['slotTypes'].append({
						'name': entityName,
						'matchingStrictness': entity['matchingStrictness'],
						'automaticallyExtensible': entity['automaticallyExtensible'],
						'useSynonyms': entity['useSynonyms'],
						'values': values
					})
					moduleSyncState['slotTypes'][entityName] = {
						'entityId': entity['id'],
						'hash': ''
					}

				for slot in intent['slots']:
					slots.append({
						'name': skillNameToCamelCase(slot['name']),
						'description': slot['description'],
						'required': slot['required'],
						'type': slot['entityId'] if slot['entityId'].startswith('snips/') else typeEntityMatching[slot['entityId']],
						'missingQuestion': slot['missingQuestion']
					})

				modules[moduleName]['intents'].append({
					'name': intentName,
					'description': intent['description'],
					'enabledByDefault': intent['enabledByDefault'],
					'utterances': utterances,
					'slots': slots
				})
				moduleSyncState['intents'][intentName] = {
					'intentId': intent['id'],
					'hash': ''
				}


			# Persist module configuration
			moduleConfig = modules[moduleName]
			moduleIntentsMountpoint = os.path.join(self.SAVED_MODULES_DIR, moduleName, 'dialogTemplate')
			os.makedirs(moduleIntentsMountpoint, exist_ok=True)

			with open(os.path.join(moduleIntentsMountpoint, '{}.json'.format(languageFilter)), 'w') as moduleConfigFile:
				json.dump(obj=moduleConfig, fp=moduleConfigFile, indent=4, sort_keys=False, ensure_ascii=False)
				self._ctx.log('[LocalModule] Finished for module {}'.format(moduleName))

