# *-* encoding: utf-8 *-*

# This is example cBot plugin
cmds = ['ping', 'test']

def action(event, body, message_type):
	if body[0] == "ping":
		event.reply("O_o").send()
	elif body[0] == "test":
		event.reply("T_T").send()
