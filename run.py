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
		self.counters = {
			'total_commands': 0,
			'total_plugins': 0
		}
		self.users = {}
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

		self.register_handlers()

	def format_platform(self, platform):
		return platform.format(
			python_version = self.python_version, 
			os_name = sys.platform.capitalize()
		)

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
		self.muc_list = []
		for muc in self.settings['muc']['list'].split(","):
			conference, nickname = muc.split("/")
			self.muc_list.append({'conference': conference, 'nickname': nickname})

		self.have_prefix = self.settings['muc']['prefix'] != ""
		if self.have_prefix: self.prefix = self.settings['muc']['prefix']

		self.nicknames = [muc['nickname'] for muc in self.muc_list]

	def join_muc(self, conference, nickname):
		log("Joining to {conference} with nickname: {nickname}".format(
				conference=colored(conference, "red"), 
				nickname=colored(nickname, "cyan")
		))
		for handler, function in self.start_handlers.items():
			if handler.startswith("muc"):
				self.register_muc_handler(handler, function, conference)
		self.plugin['xep_0045'].joinMUC(conference, nickname, wait=True)

	def register_muc_handler(self, handler, function, conference):
		handler = handler.format(conference=conference)
		log("Registering MUC handler: {handler}".format(
			handler=handler.replace(conference, colored(conference, "red"))
		))
		self.add_event_handler(handler, function)		

	def register_handlers(self):
		for handler, function in self.start_handlers.items():
			if not handler.startswith("muc"):
				log("Registering handler: {handler}".format(handler=handler))
				self.add_event_handler(handler, function)

	def join_mucs(self):
		for muc in self.muc_list:
			self.join_muc(muc['conference'], muc['nickname'])

	def session_start(self, event):
		self.send_presence()
		self.get_roster()
		self.join_mucs()

	def get_message_type(self, event):
		return 'normal' if event['type'] in ('chat', 'normal') else 'groupchat'

	def get_shortname(self, event, old_method = False):
		if old_method: return str(event['from']).split("/")[1]
		else: return event['mucnick']

	def get_muc(self, event):
		return str(event['from']).split("/")[0]

	def get_command(self, command):
		for cmd_name, aliases in self.plugins['commands'].items():
			if command in aliases:
				return cmd_name
		return None

	def reply(self, event, text, with_nickname = True):
		message_type = self.get_message_type(event)

		if message_type == "normal": text = text.capitalize()
		elif message_type == "groupchat" and with_nickname: text = "{nickname}: ".format(nickname=self.get_shortname(event)) + text

		event.reply(text).send()

	def message_received(self, event):
		if self.have_prefix and event['body'].startswith(self.prefix): body = event['body'][len(self.prefix):].split(" ", 1)
		else: body = event['body'].split(" ", 1)

		if len(body) == 1: body = body + ['']

		# Command handler
		cmd = body[0]
		args = body[1].split(" ")

		if self.get_command(cmd) != None:
			if self.have_prefix and event['body'].startswith(self.prefix) or not self.plugins['info'][cmd]['need_prefix']: 
				if self.get_shortname(event) not in self.nicknames:
					if self.users[str(event['from'])]['privlevel'] >= self.plugins['info'][cmd]['privlevel']:
						self.call_plugin(event, body, args, self, self.get_message_type(event))
					else:
						self.reply(event, "Not enough permissions!")

	def get_filepaths(self, directory):
		file_paths = []

		for root, directories, files in os.walk(directory):
			for filename in files:
				filepath = os.path.join(root, filename)
				file_paths.append(filepath)

		return file_paths

	def load_plugins(self):
		commands = {}
		info = {}
		for filepath in self.get_filepaths("plugins"):
			if filepath.endswith(".py"):
				plugin_name = filepath.split("/")[-1][:-3]
				plugin_path = filepath.replace("/", ".")[:-3]
				if plugin_name != "__init__":
					plugins_import = __import__(plugin_path)
					plugin = getattr(plugins_import, plugin_name)
					for cmd_name, data in plugin.metainfo.items():
						copy_of_data = data.copy()
						copy_of_data.update({'category': plugin_name})
						info[cmd_name] = copy_of_data 
						
						# Looks like so: {'ping': ['ping', 'пинг']}
						commands[cmd_name] = [cmd_name] if len(data['aliases']) == 0 else [cmd_name] + data['aliases']

						self.counters['total_commands'] += len(commands[cmd_name])
						self.counters['total_plugins'] += 1

						log("Loaded plugin: {category}:{cmd_name}. Commands: {commands}".format(
							category = plugin_name,
							cmd_name = cmd_name,
							commands = ', '.join(commands[cmd_name]).replace(cmd_name, colored(cmd_name, "yellow"))
						))

		log("Total plugins loaded: %s" % colored(str(self.counters['total_plugins']), "magenta", attrs=['bold']))
		log("Total commands: %s" % colored(str(self.counters['total_commands']), "magenta", attrs=['bold']))
		return {'attrs': plugins_import, 'commands': commands, 'info': info}

	def call_plugin(self, event, body, args, bot, message_type):
		cmd = self.get_command(body[0])
		plugin = getattr(self.plugins['attrs'], self.plugins['info'][cmd]['category'])
		self.plugins['info'][cmd]['function'](event, body, args, bot, message_type)

	def presence_reply(self, presence, text, message_type = 'groupchat'):
		self.send_message(mto=presence['from'].bare, mbody=text, mtype=message_type)

	def muc_online(self, presence):
		if presence['muc']['nick'] not in self.nicknames:
			nick = presence['muc']['nick']
			room = self.get_muc(presence)
			affiliation = str(presence['muc']['affiliation'])

			if affiliation == "owner": privlevel = 10
			elif affiliation == "admin": privlevel = 5
			else: privlevel = 1

			self.users[room + "/" + nick] = {
				'privlevel': privlevel
			}
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