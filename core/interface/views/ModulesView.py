import json
from pathlib import Path

import requests
from flask import jsonify, render_template, request

from core.base.model.GithubCloner import GithubCloner
from core.base.model.Version import Version
from core.commons import constants
from core.interface.model.View import View


class ModulesView(View):
	route_base = '/modules/'


	def index(self):
		modules = {**self.SkillManager.activeModules, **self.SkillManager.deactivatedModules}
		modules = {skillName: module for skillName, module in sorted(modules.items()) if module is not None}

		return render_template(template_name_or_list='modules.html',
		                       modules=modules,
		                       langData=self._langData,
		                       aliceSettings=self.ConfigManager.aliceConfigurations)


	def toggleModule(self):
		try:
			_, module = request.form.get('id').split('_')
			if self.SkillManager.isModuleActive(module):
				self.SkillManager.deactivateModule(skillName=module, persistent=True)
			else:
				self.SkillManager.activateModule(skillName=module, persistent=True)
		except Exception as e:
			self.logWarning(f'Failed toggling module: {e}', printStack=True)
		
		return self.index()


	def deleteModule(self):
		try:
			_, module = request.form.get('id').split('_')
			self.SkillManager.removeModule(module)
		except Exception as e:
			self.logWarning(f'Failed deleting module: {e}', printStack=True)

		return self.index()


	def saveModuleSettings(self):
		skillName = request.form['skillName']
		for confName, confValue in request.form.items():
			if confName == 'skillName':
				continue

			if confValue == 'on':
				confValue = True
			elif confValue == 'off':
				confValue = False

			self.ConfigManager.updateModuleConfigurationFile(
				skillName=skillName,
				key=confName,
				value=confValue
			)

		return self.index()


	def installModules(self):
		try:
			modules = request.json

			for module in modules:
				self.WebInterfaceManager.newModuleInstallProcess(module['module'])
				req = requests.get(f'https://raw.githubusercontent.com/project-alice-assistant/ProjectAliceModules/{self.ConfigManager.getSkillsUpdateSource()}/PublishedModules/{module["author"]}/{module["module"]}/{module["module"]}.install')
				remoteFile = req.json()
				if not remoteFile:
					self.WebInterfaceManager.moduleInstallProcesses[module['module']]['status'] = 'failed'
					continue

				moduleFile = Path(self.Commons.rootDir(), f'system/moduleInstallTickets/{module["module"]}.install')
				moduleFile.write_text(json.dumps(remoteFile))

			return jsonify(success=True)
		except Exception as e:
			self.logWarning(f'Failed installing module: {e}', printStack=True)
			return jsonify(success=False)


	def checkInstallStatus(self):
		module = request.form.get('module')
		status = self.WebInterfaceManager.moduleInstallProcesses.get(module, {'status': 'unknown'})['status']
		return jsonify(status)


	def loadStoreData(self):
		installers = dict()
		updateSource = self.ConfigManager.getSkillsUpdateSource()
		req = requests.get(
			url='https://api.github.com/search/code?q=extension:install+repo:project-alice-assistant/ProjectAliceModules/',
			auth=GithubCloner.getGithubAuth())
		results = req.json()
		if results:
			for module in results['items']:
				try:
					req = requests.get(
						url=f"{module['url'].split('?')[0]}?ref={updateSource}",
						headers={'Accept': 'application/vnd.github.VERSION.raw'},
						auth=GithubCloner.getGithubAuth()
					)
					installer = req.json()
					if installer:
						installers[installer['name']] = installer

				except Exception:
					continue

		actualVersion = Version(constants.VERSION)
		return {
			skillName: moduleInfo for skillName, moduleInfo in installers.items()
			if self.SkillManager.getModuleInstance(skillName=skillName, silent=True) is None and actualVersion >= Version(moduleInfo['aliceMinVersion'])
		}
