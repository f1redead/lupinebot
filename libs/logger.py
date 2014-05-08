from . import termcolor
import time

class Logger:
	def __init__(self, debug=False, color=True):
		self.color_mode = color
		self.debug_mode = debug

	def colored(self, text, color=None, on_color=None, attrs=None):
		if self.color_mode: return termcolor.colored(text, color, on_color, attrs)
		else: return text

	def log(self, message, level = 1):
		try: prefix = {0: self.colored('DEBUG', 'grey', attrs=['bold']),
						1: self.colored('INFO', 'cyan', attrs=['bold']), 
						2: self.colored('WARN', 'yellow', attrs=['bold']), 
						3: self.colored('ERROR', 'red', attrs=['bold'])}[level]
		except KeyError: prefix = 'undef'
		message = "[{datetime} {prefix}] {message}".format(datetime=time.strftime("%H:%M:%S", time.localtime()), prefix=prefix, message=message)
		if level == 0 and self.debug_mode is True: print(message)
		elif level != 0: print(message)
