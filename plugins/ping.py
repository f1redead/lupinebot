# *-* encoding: utf-8 *-*

# This is example cBot plugin

def action(event, body, message_type):
	event.reply("Pong!").send()
