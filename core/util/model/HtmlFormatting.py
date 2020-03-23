import logging
from typing import Match

import re
from enum import Enum


class HtmlFormatting(Enum):
	LOG = '<span class="logLine {}">{}</span>'
	INLINE = '<span class="{}">{}</span>'

	BOLD = 'logBold'
	DIM = 'logDim'
	UNDERLINED = 'logUnderlined'

	DEFAULT = 'logDefault'
	RED = 'logRed'
	GREEN = 'logGreen'
	YELLOW = 'logYellow'
	BLUE = 'logBlue'
	GREY = 'logGrey'


class Formatter(logging.Formatter):
	BOLD = re.compile(r'\*\*(.+?)\*\*')
	DIM = re.compile(r'--(.+?)--')
	UNDERLINED = re.compile(r'__(.+?)__')
	COLOR = re.compile(r'(?i)!\[(red|green|yellow|blue|grey)\]\((.+?)\)')

	COLORS = {
		'WARNING' : HtmlFormatting.YELLOW.value,
		'INFO'    : HtmlFormatting.DEFAULT.value,
		'DEBUG'   : HtmlFormatting.BLUE.value,
		'ERROR'   : HtmlFormatting.RED.value,
		'CRITICAL': HtmlFormatting.RED.value
	}


	def __init__(self):
		mask = '%(message)s'
		super().__init__(mask)


	def format(self, record: logging.LogRecord) -> str:
		level = record.levelname
		msg = record.getMessage()

		if level in self.COLORS:
			msg = HtmlFormatting.LOG.value.format(self.COLORS[level], msg)

		msg = self.BOLD.sub(HtmlFormatting.INLINE.value.format(HtmlFormatting.BOLD.value, r'\1'), msg)
		msg = self.UNDERLINED.sub(HtmlFormatting.INLINE.value.format(HtmlFormatting.UNDERLINED.value, r'\1'), msg)
		msg = self.DIM.sub(HtmlFormatting.INLINE.value.format(HtmlFormatting.DIM.value, r'\1'), msg)
		msg = self.COLOR.sub(self.colorFormat, msg)

		return msg


	@staticmethod
	def colorFormat(m: Match) -> str:
		color = m.group(1).title()
		return HtmlFormatting.INLINE.value.format(f'log{color}', m.group(2))
