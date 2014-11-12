from collections import OrderedDict
from collections import namedtuple
from stomp.utils import Frame, convert_frame_to_lines

import json
import pkg_resources
import re
import sys

StompMessage = namedtuple('StompMessage', ['command', 'body', 'json', 'headers'])


class StompAccessDenied(Exception):
    """
    """


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
        match = re.search(r'^(\w+)\n(.*?)\n\n(.*?)\x00?$', message, re.DOTALL)
        if match is None:
            raise Exception('Stomp decode error: {}'.format(message))

        command, header, body = match.groups()
        headers = dict(re.findall(r'\n?([^:]+):(.*)', header))

        try:
            decoded_body = json.loads(body) if body else body
            return StompMessage(command, body, decoded_body, headers)
        except:
            if 'Access refused' in body:
                raise StompAccessDenied(body)

    def connect_frame(self, login, passcode, **extra_headers):
        """
            Returns a STOMP CONNECT frame.
        """
        headers = OrderedDict()
        headers["login"] = login
        headers["passcode"] = passcode
        headers["host"] = "/"
        headers["accept-version"] = "1.1,1.0"
        headers["heart-beat"] = "0,0"
        headers["product-version"] = pkg_resources.require('utalk-python-client')[0].version
        headers["platform"] = 'Python {0.major}.{0.minor}.{0.micro}'.format(sys.version_info),

        headers.update(extra_headers)
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
