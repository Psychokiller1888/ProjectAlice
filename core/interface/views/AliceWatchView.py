from pathlib import Path

import tempfile
from flask import jsonify, render_template, request

from core.interface.model.View import View


class AliceWatchView(View):
	route_base = '/alicewatch/'


	def __init__(self):
		super().__init__()
		self._counter = 0
		self._thread = None
		self._file = Path(tempfile.gettempdir(), 'snipswatch')
		self._process = None


	def index(self):
		self.SnipsWatchManager.startWatching()
		return render_template(template_name_or_list='alicewatch.html',
		                       langData=self._langData,
		                       aliceSettings=self.ConfigManager.aliceConfigurations)


	def refreshConsole(self):
		return jsonify(data=self.SnipsWatchManager.getLogs())


	def verbosity(self):
		try:
			if self._process:
				self._process.terminate()

			verbosity = int(request.form.get('verbosity'))
			self.SnipsWatchManager.setVerbosity(verbosity)
			return self.refreshConsole()
		except Exception as e:
			self.log.error(f'Error setting verbosity: {e}')
			return jsonify(success=False)



