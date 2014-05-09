# *-* encoding: utf-8 *-*

# Python 3.x

from sleekxmpp import *
from configparser import ConfigParser
from libs.logger import Logger
import sys
import os
import json
import getpass
import logging

class XMPPBot(ClientXMPP):
	def __init__(self):
		self.start_handlers = {
								'session_start': self.session_start,
								'message': self.message_received,
								'muc::{conference}::got_online': self.muc_online	
							}
		self.xeps_to_load = ["xep_0092", "xep_0045"]
		self.read_configs()

	def post_init(self):
		ClientXMPP.__init__(self, self.settings['auth']['jid'], self.settings['auth']['password'])
		self.settings['auth']['password'] = ""

		# Settings dump just for sure
		log('\n' + json.dumps(self.settings, indent=4), 0)

		# Now.. We starting!
		self. python_version = '.'.join([str(n) for n in list(sys.version_info)][:3])
		log("I'm running at Python {version}".format(version=self.python_version))
		log("My JID is {jid}".format(jid=colored(self.settings['auth']['jid'], "cyan")))

		self.plugins = self.load_plugins()
		log("Plugins list: " + ', '.join(self.plugins['commands']))
		log(self.plugins['info'])
		self.register_handlers()

	def format_platform(self, platform):
		return platform.format(python_version = self.python_version, os_name = sys.platform.capitalize())

	def read_configs(self):
		self.settings = {}
		for config_name in os.listdir("config"):
			config_inst = ConfigParser()
			config_inst.readfp(open("config/"+config_name))
			for section in config_inst.sections():
				self.settings[section] = {}
				for item, value in config_inst.items(section):
					self.settings[section][item] = value
					if section == "auth" and item == "password" and value == "":
						self.settings[section][item] = getpass.getpass("Enter password for {jid}: ".format(jid=self.settings['auth']['jid']))
					elif value in ("0", "1"):
						self.settings[section][item] = config_inst.getboolean(section, item)
		self.muc_list = self.settings['muc']['list'].split(",")

	def register_handlers(self):
		for handler, function in self.start_handlers.items():
			if handler.startswith("muc"):
				for muc in self.muc_list:
					handler = handler.format(conference=muc)
					log("Registering MUC handler: {handler}".format(handler=handler.replace(muc, colored(muc, "red"))))
					self.add_event_handler(handler, function)
			else:
				log("Registering handler: {handler}".format(handler=handler))
				self.add_event_handler(handler, function)

	def join_mucs(self):
		for muc in self.muc_list:
			self.plugin['xep_0045'].joinMUC(muc, self.settings['muc']['nickname'], wait=True)

	def session_start(self, event):
		self.send_presence()
		self.get_roster()
		self.join_mucs()

	def message_received(self, event):
		body = event['body'].split(" ", 1)
		message_type = 'normal' if event['type'] in ('chat', 'normal') else 'groupchat'
		self.command_handler(event, body, message_type)

	def get_filepaths(self, directory):
	    file_paths = []

	    for root, directories, files in os.walk(directory):
	        for filename in files:
	            filepath = os.path.join(root, filename)
	            file_paths.append(filepath)

	    return file_paths

	def command_handler(self, event, body, message_type):
		if body[0] in self.plugins['commands']:
			self.call_plugin(event, body, message_type)

	def load_plugins(self):
		commands = []
		info = {}
		for filepath in self.get_filepaths("plugins"):
			if filepath.endswith(".py"):
				plugin_name = filepath.split("/")[-1][:-3]
				plugin_path = filepath.replace("/", ".")[:-3]
				if plugin_name != "__init__":
					plugins_import = __import__(plugin_path)
					plugin = getattr(plugins_import, plugin_name)
					# Like so: {'ping': 'misc'}
					for cmd in plugin.cmds:
						info[cmd] = plugin_name
					commands.extend(plugin.cmds)
		return {'attrs': plugins_import, 'commands': commands, 'info': info}

	def call_plugin(self, event, body, message_type):
		plugin = getattr(self.plugins['attrs'], self.plugins['info'][body[0]])
		plugin.action(event, body, message_type)

	def muc_online(self, event):
		pass
		# You can do many cool things in this place, yes..

if __name__ == "__main__":
	bot = XMPPBot()

	config = bot.settings

	logger = Logger(config['settings']['debug'], config['settings']['color'])
	log = logger.log
	colored = logger.colored

	if config['settings']['hard_debug']: logging.basicConfig(level=logging.DEBUG, format='%(levelname)-8s %(message)s')

	bot.post_init()
	for xep in bot.xeps_to_load:
		bot.register_plugin(xep)

	if "xep_0092" in bot.xeps_to_load:
		bot['xep_0092'].software_name = config['settings']['bot_name']
		bot['xep_0092'].version = config['settings']['bot_version']
		bot['xep_0092'].os = bot.format_platform(config['settings']['bot_platform'])

	log("Connecting...")
	if bot.connect():
		log(colored("Online!", "green"))

		try: bot.process(block=True)
		except KeyboardInterrupt:
			log("Got Ctrl-C. Going to shutdown.", 3)
	else:
		log("Failed to connect.", 3)