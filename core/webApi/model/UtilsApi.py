from flask import jsonify, request
from flask_classful import route

from core.interface.model.Api import Api
from core.util.Decorators import ApiAuthenticated


class UtilsApi(Api):
	route_base = f'/api/{Api.version()}/utils/'


	def __init__(self):
		super().__init__()


	@route('/restart/')
	@ApiAuthenticated
	def restart(self):
		try:
			self.ThreadManager.doLater(interval=2, func=self.ProjectAlice.doRestart)
			return jsonify(success=True)
		except Exception as e:
			self.logError(f'Failed restarting Alice: {e}')
			return jsonify(success=False)


	@route('/reboot/')
	@ApiAuthenticated
	def reboot(self):
		try:
			self.ThreadManager.doLater(interval=2, func=self.Commons.runRootSystemCommand, args=[['shutdown', '-r', 'now']])
			return jsonify(success=True)
		except Exception as e:
			self.logError(f'Failed rebooting device: {e}')
			return jsonify(success=False)


	@route('/config/', methods=['GET'])
	def config(self):
		"""
		Returns Alice configs. If authenticated, with passwords, if not, sensitive data is removed
		"""
		try:
			configs = self.ConfigManager.aliceConfigurations
			configs['aliceIp'] = self.Commons.getLocalIp()
			configs['apiPort'] = self.ConfigManager.getAliceConfigByName('apiPort')
			if not self.UserManager.apiTokenValid(request.headers.get('auth', '')):
				configs = {key: value for key, value in configs.items() if not self.ConfigManager.isAliceConfSensitive(key)}

			return jsonify(config=configs)
		except Exception as e:
			self.logError(f'Failed retrieving Alice configs: {e}')
			return jsonify(success=False)


	@route('/mqttConfig/', methods=['GET'])
	def mqttConfig(self):
		return jsonify(
			success=True,
			host=self.Commons.getLocalIp(),
			port=int(self.ConfigManager.getAliceConfigByName('mqttPort')) + 1
		)