from collections import OrderedDict
from maxcarrot import RabbitMessage
from stomp.utils import Frame, convert_frame_to_lines

import re


def forge_message(command, headers, body):
    frame = Frame(command, headers, body)
    message = convert_frame_to_lines(frame)
    return '["' + ''.join(message[:-1]) + '"]'


class StompClient(object):
    def __init__(self, domain, username, passcode, sockjs_client):
        self.domain = domain
        self.username = username
        self.auth_username = username if domain is None else '{}:{}'.format(domain, username)
        self.passcode = passcode
        self.sockjs = sockjs_client

    @property
    def ws(self):
        return self.sockjs.ws

    def connect(self):
        headers = OrderedDict()
        headers["login"] = self.auth_username
        headers["passcode"] = self.passcode
        headers["host"] = "/"
        headers["accept-version"] = "1.1,1.0"
        headers["heart-beat"] = "0,0"

        message = forge_message('CONNECT', headers, '\u0000')
        self.ws.send(message)
        print '> Started stomp session as {}'.format(self.username)

    def subscribe(self):
        headers = OrderedDict()
        headers["id"] = "sub-0",
        headers["destination"] = "/exchange/{}.subscribe".format(self.username),

        message = forge_message('SUBSCRIBE', headers, '\u0000')
        self.ws.send(message)
        print '> Listening on {} messages'.format(self.username)
        print

    def receive(self, headers, body):
        message = RabbitMessage.unpack(body)
        destination = re.search(r'([0-9a-f]+).(?:notifications|messages)', headers['destination']).groups()[0]
        if message['action'] == 'add' and message['object'] == 'message':
            print '> {}@{}: {}'.format(message['user']['username'], destination, message['data']['text'])
