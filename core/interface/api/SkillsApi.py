import json
from pathlib import Path

import requests
from flask import jsonify, request
from flask_classful import route

from core.interface.model.Api import Api
from core.util.Decorators import ApiAuthenticated


class SkillsApi(Api):
	route_base = f'/api/{Api.version()}/skills/'


	def __init__(self):
		super().__init__()


	def index(self):
		return jsonify(data=[skill.toJson() for skill in self.SkillManager.allSkills.values()])


	@ApiAuthenticated
	def delete(self, skillName: str):
		if skillName in self.SkillManager.neededSkills:
			return jsonify(success=False, reason='skill cannot be deleted')

		try:
			self.SkillManager.removeSkill(skillName)
			return jsonify(success=True)
		except Exception as e:
			return jsonify(success=False, reason=f'Failed deleting skill: {e}')


	def get(self, skillName: str):
		skill = self.SkillManager.getSkillInstance(skillName=skillName, silent=True)
		skill = skill.toJson() if skill else dict()

		return jsonify(data=skill)


	@route('/<skillName>/toggleActiveState/')
	@ApiAuthenticated
	def toggleActiveState(self, skillName: str):
		if skillName not in self.SkillManager.allSkills:
			return jsonify(success=False, reason='skill not found')

		if self.SkillManager.isSkillActive(skillName):
			if skillName in self.SkillManager.neededSkills:
				return jsonify(success=False, reason='skill cannot be deactivated')

			self.SkillManager.deactivateSkill(skillName=skillName, persistent=True)
		else:
			self.SkillManager.activateSkill(skillName=skillName, persistent=True)

		return jsonify(success=True)


	@route('/<skillName>/activate/', methods=['GET', 'POST'])
	@ApiAuthenticated
	def activate(self, skillName: str):
		if skillName not in self.SkillManager.allSkills:
			return jsonify(success=False, reason='skill not found')

		if self.SkillManager.isSkillActive(skillName):
			return jsonify(success=False, reason='already active')
		else:
			persistent = request.form.get('persistent') is not None and request.form.get('persistent') == 'true'
			self.SkillManager.activateSkill(skillName=skillName, persistent=persistent)
			return jsonify(success=True)


	@route('/<skillName>/deactivate/', methods=['GET', 'POST'])
	@ApiAuthenticated
	def deactivate(self, skillName: str):
		if skillName not in self.SkillManager.allSkills:
			return jsonify(success=False, reason='skill not found')

		if skillName in self.SkillManager.neededSkills:
			return jsonify(success=False, reason='skill cannot be deactivated')

		if self.SkillManager.isSkillActive(skillName):
			persistent = request.form.get('persistent') is not None and request.form.get('persistent') == 'true'
			self.SkillManager.deactivateSkill(skillName=skillName, persistent=persistent)
			return jsonify(success=True)
		else:
			return jsonify(success=False, reason='not active')


	@route('/<skillName>/reload/', methods=['GET', 'POST'])
	@ApiAuthenticated
	def reload(self, skillName: str):
		if skillName not in self.SkillManager.allSkills:
			return jsonify(success=False, reason='skill not found')

		try:
			self.log.info(f'Reloading skill "{skillName}"')
			self.SkillManager.reloadSkill(skillName)
		except Exception as e:
			self.log.warning(f'Failed reloading skill: {e}', printStack=True)
			return jsonify(success=False)

		return jsonify(success=True)


	@ApiAuthenticated
	def put(self, skillName: str):
		if not self.SkillStoreManager.skillExists(skillName):
			return jsonify(success=False, reason='skill not found')
		elif self.SkillManager.getSkillInstance(skillName, True) is not None:
			return jsonify(success=False, reason='skill already installed')

		try:
			req = requests.get(f'https://raw.githubusercontent.com/project-alice-assistant/skill_{skillName}/{self.SkillStoreManager.getSkillUpdateTag(skillName)}/{skillName}.install')
			remoteFile = req.json()
			if not remoteFile:
				return jsonify(success=False, reason='skill not found')

			skillFile = Path(self.Commons.rootDir(), f'system/skillInstallTickets/{skillName}.install')
			skillFile.write_text(json.dumps(remoteFile))
		except Exception as e:
			self.log.warning(f'Failed installing skill: {e}', printStack=True)
			return jsonify(success=False)

		return jsonify(success=True)


	@route('/<skillName>/checkUpdate/')
	def checkUpdate(self, skillName: str):
		if skillName not in self.SkillManager.allSkills:
			return jsonify(success=False, reason='skill not found')

		return jsonify(success=self.SkillManager.checkForSkillUpdates(skillToCheck=skillName))
