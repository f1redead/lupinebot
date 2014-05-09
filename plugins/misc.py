# *-* encoding: utf-8 *-*

# This is example cBot plugin

def ping(event, body, args, bot, message_type):
	bot.reply(event, "pong!")

def say(event, body, args, bot, message_type):
	bot.reply(event, body[1], with_nickname = False)

def join(event, body, args, bot, message_type):
	if len(args) == 2:
		conference, nickname = args
		bot.join_muc(conference, nickname)

metainfo = {
	'ping': {'function': ping, 'descr': "Понг!", 'privlevel': 1, 'aliases': ['пинг'], 'need_prefix': False},
	'say': {'function': say, 'descr': "Отправит сообщение от имени бота", 'privlevel': 100, 'aliases': ['сказать'], 'need_prefix': True},
	'join': {'function': join, 'descr': "Зайти в комнату", 'privlevel': 100, 'aliases': ['зайти'], 'need_prefix': True}
}