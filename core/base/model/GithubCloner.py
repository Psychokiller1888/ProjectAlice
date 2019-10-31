from pathlib import Path

import requests
import shutil

from core.ProjectAliceExceptions import GithubRateLimit, GithubTokenFailed
from core.base.model.ProjectAliceObject import ProjectAliceObject


class GithubCloner(ProjectAliceObject):

	NAME = 'GithubCloner'

	def __init__(self, baseUrl: str, path: Path, dest: Path):
		super().__init__(logDepth=3)
		self._baseUrl = baseUrl
		self._path = path
		self._dest = dest


	def clone(self) -> bool:
		if self._dest.exists():
			self._cleanDestDir()
		else:
			self._dest.mkdir(parents=True)

		try:
			return self._doClone(f'https://api.github.com/{self._baseUrl}/{self._path}?ref={self.ConfigManager.getAliceConfigByName("updateChannel")}')
		except:
			return False


	def _doClone(self, url: str) -> bool:
		try:
			username = self.ConfigManager.getAliceConfigByName('githubUsername')
			token = self.ConfigManager.getAliceConfigByName('githubToken')

			auth = (username, token) if (username and token) else None

			req = requests.get(url, auth=auth)
			if req.status_code == 401:
				raise GithubTokenFailed
			elif req.status_code == 403:
				raise GithubRateLimit
			elif req.status_code != 200:
				raise Exception

			data = req.json()
			for item in data:
				path = Path(*Path(item['path']).parts[3:])
				if item['type'] == 'file':
					if path.suffix == '.install':
						continue

					fileStream = requests.get(url=item['download_url'], auth=auth)
					Path(self._dest / path).write_bytes(fileStream.content)
				else:
					Path(self._dest / path).mkdir(parents=True)
					self._doClone(url=item['url'])

			return True

		except GithubTokenFailed:
			self.logError('Provided Github username / token invalid')
			return False

		except GithubRateLimit:
			self.logError('Github rate limit reached, cannot access updates for now. You should consider creating a token to avoid this problem')
			return False

		except Exception as e:
			self.logError(f'Error downloading module: {e}')
			raise


	def _cleanDestDir(self):
		filesToDelete = list()
		directoriesToDelete = list()
		for file in self._dest.iterdir():
			if file.suffix == '.conf' or file.with_suffix('.dist').exists():
				continue

			if (file.is_dir() and not file.name.startswith('_')) or file.name == '__pycache__':
				directoriesToDelete.append(file)

			elif file.is_file():
				filesToDelete.append(file)

		# Not deleting directories and files directly because they are needed for the .dist check
		for directory in directoriesToDelete:
			shutil.rmtree(directory)

		for file in filesToDelete:
			file.unlink()
