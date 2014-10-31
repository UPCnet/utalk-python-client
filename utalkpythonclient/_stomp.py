from collections import OrderedDict
from collections import namedtuple
from stomp.utils import Frame, convert_frame_to_lines

import json
import re

StompMessage = namedtuple('StompMessage', ['command', 'body', 'json', 'headers'])


def forge_message(command, headers, body):
    frame = Frame(command, headers, body)
    message = convert_frame_to_lines(frame)
    return '["' + ''.join(message[:-1]) + '"]'


class StompHelper(object):

    def decode(self, message):
        command, header, body = re.search(r'(\w+)\\n(.*)\\n([^\n]+)', message).groups()
        headers = dict(re.findall(r'([^:]+):(.*?)\\n?', header, re.DOTALL | re.MULTILINE))

        try:
            decoded_body = json.loads(body.replace('\\', ''))
        except:
            decoded_body = ''

        return StompMessage(command, body, decoded_body, headers)

    def connect_frame(self, login, passcode):
        headers = OrderedDict()
        headers["login"] = login
        headers["passcode"] = passcode
        headers["host"] = "/"
        headers["accept-version"] = "1.1,1.0"
        headers["heart-beat"] = "0,0"

        message = forge_message('CONNECT', headers, '\u0000')
        return message

    def subscribe_frame(self, username):
        headers = OrderedDict()
        headers["id"] = "sub-0",
        headers["destination"] = "/exchange/{}.subscribe".format(username),

        message = forge_message('SUBSCRIBE', headers, '\u0000')
        return message
