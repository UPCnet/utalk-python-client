from collections import OrderedDict
from collections import namedtuple
from stomp.utils import Frame, convert_frame_to_lines

import json
import re

StompMessage = namedtuple('StompMessage', ['command', 'body', 'json', 'headers'])


def forge_message(command, headers, body=''):
    """
        Returns a STOMP compliant frame.
    """
    frame = Frame(command, headers, body)
    message = convert_frame_to_lines(frame)
    return ''.join(message[:-1]) + '\u0000'


class StompHelper(object):

    def decode(self, message):
        """
            Decodes the parts of a STOMP Frame.
            Tries to decode the body as json.
        """
        command, header, body = re.search(r'^(\w+)\n(.*?)\n\n(.*?)\x00?$', message, re.DOTALL).groups()
        headers = dict(re.findall(r'\n?([^:]+):(.*)', header))

        try:
            decoded_body = json.loads(body)
        except:
            decoded_body = ''

        return StompMessage(command, body, decoded_body, headers)

    def connect_frame(self, login, passcode):
        """
            Returns a STOMP CONNECT frame.
        """
        headers = OrderedDict()
        headers["login"] = login
        headers["passcode"] = passcode
        headers["host"] = "/"
        headers["accept-version"] = "1.1,1.0"
        headers["heart-beat"] = "0,0"

        message = forge_message('CONNECT', headers)
        return message

    def subscribe_frame(self, destination):
        """
            Returns a STOMP SUBSCRIBE frame.
        """
        headers = OrderedDict()
        headers["id"] = "sub-0",
        headers["destination"] = destination

        message = forge_message('SUBSCRIBE', headers)
        return message

    def send_frame(self, headers, body):
        """
            Returns a STOMP SEND frame
        """
        message = forge_message('SEND', headers, body)
        return message
