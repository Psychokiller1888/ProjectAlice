from typing import Any

from core.base.model.ProjectAliceObject import ProjectAliceObject
from core.scenario.model.ScenarioTileType import ScenarioTileType


class ScenarioTile(ProjectAliceObject):

	def __init__(self):
		super().__init__(name='')
		self.tileType: ScenarioTileType = ScenarioTileType.ACTION
		self.description: str = ''
		self.value: Any = ''


	def interfaceName(self) -> str:
		return self.name
