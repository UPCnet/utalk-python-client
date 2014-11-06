from collections import namedtuple
from ws4py.client.threadedclient import WebSocketClient

import json
import random
import re
import requests
import string
import wsaccel

wsaccel.patch_ws4py()

SOCKJS_CONNECTED = object()
SOCKJS_MESSAGE = object()
SOCKJS_HEARTBEAT = object()
SOCKJS_UNKNOWN = object()
SOCKJS_CLOSE = object()

SOCKJS_TYPES = {
    'o': SOCKJS_CONNECTED,
    'h': SOCKJS_HEARTBEAT,
    'a': SOCKJS_MESSAGE,
    'm': SOCKJS_MESSAGE,
    'c': SOCKJS_CLOSE,

}

Message = namedtuple('Message', ['opcode', 'type', 'content'])


class SockJSTransport(object):
    transport_id = ''
    transport_send_id = ''
    regular_schema = ''
    secure_schema = ''

    frame = namedtuple('SockJSFrame', ['data'])

    def __init__(self, url, prefix):
        schema, host, port, path = re.match(r'(\w+)?(?:://)?([^:/]+)(?::(\d+))?/?(.*?)/?$', url).groups()

        # If schema not defined, determine by its port
        if schema is None:
            schema = self.secure_schema if port == 443 else self.regular_schema

        # if port is not defined define it by its schema
        if port is None:
            port = 443 if schema == self.secure_schema else 80

        path = path.strip('/')
        prefix = prefix.strip('/')
        server_id = str(random.randint(0, 1000))
        client_id = self.random_str(8)

        self.schema = schema
        self.port = port
        self.host = host
        self.prefix = prefix

        self.transport_id = self.transport_id
        self.transport_send_id = self.transport_send_id

        regular_http = self.port == 80 and self.schema == self.regular_schema
        regular_https = self.port == 443 and self.schema == self.secure_schema
        self.port_bit = '' if regular_http or regular_https else ':{}'.format(port)

        self.base_path = '/'.join([path, prefix]).replace('//', '/')
        self.path = '/'.join([self.base_path, server_id, client_id])
        self.closing = False

    @staticmethod
    def random_str(length):
        letters = string.ascii_lowercase + string.digits
        return ''.join(random.choice(letters) for c in range(length))

    @staticmethod
    def parse_sockjs(frame):
        """
            Parses a sockjs frame and extracts it's content.
        """
        try:
            opcode, body = re.search(r'([acmoh])(.*)', frame, re.DOTALL | re.MULTILINE).groups()
        except:
            return [], frame

        # Try to parse body-less frames first, if found, return remaining data
        if opcode in 'oh':
            return [Message(opcode, SOCKJS_TYPES[opcode], "")], body

        # Try to parse frames with body
        elif opcode in "acm":
            full_frames = []
            match = re.search(r'(\[".*?"\])(.*)$', frame, re.DOTALL | re.MULTILINE).groups()
            # we have a full frame
            if match:
                full, remaining = match
                sockjs_array = json.loads(full)
                for item in sockjs_array:
                    full_frames.append(Message(opcode, SOCKJS_TYPES[opcode], item))

                return full_frames, remaining
            else:
                return [], frame

        return [], ''

    def sockjs_info(self):
        response = requests.get(self.base_url + '/info')
        return response.content

    @property
    def base_url(self):
        return '{schema}://{host}{port_bit}/{base_path}'.format(**self.__dict__)

    @property
    def url(self):
        return '{schema}://{host}{port_bit}/{path}/{transport_id}'.format(**self.__dict__)

    @property
    def send_url(self):
        return '{schema}://{host}{port_bit}/{path}/{transport_send_id}'.format(**self.__dict__)

    def connect(self):
        return self._connect()

    def _connect(self):
        pass

    def send(self, message):
        wrapped = '["{}"]'.format(message)
        self._send(wrapped)
        return wrapped

    def start(self):
        self._start()

    def close(self):
        self._close()


class XHRPollingTransport(SockJSTransport):
    transport_id = 'xhr'
    transport_send_id = 'xhr_send'
    regular_schema = 'http'
    secure_schema = 'https'

    def _send(self, message):
        response = requests.post(
            self.send_url,
            message,
            headers={'Content-Type': 'text/plain'})
        return response.status_code in (200, 204)

    def _start(self):
        data = ""
        partial = ''
        while not self.closing:
            chunk = requests.post(self.url).content
            messages = []
            data = partial + chunk
            messages, partial = self.parse_sockjs(data)

            for message in messages:
                self.on_message(message)

    def _close(self):
        self.closing = True


class WebsocketTransport(SockJSTransport):
    transport_id = 'websocket'
    regular_schema = 'ws'
    secure_schema = 'wss'

    def __init__(self, url, prefix):
        super(WebsocketTransport, self).__init__(url.replace('http', 'ws'), prefix)

    def _send(self, message):
        self.ws.send(message)

    def _connect(self):
        self.ws = WebSocketClient(self.url)
        self.ws.opened = self.on_open
        self.ws.closed = self.on_close
        self.ws.received_message = self.handle_message

        self.ws.connect()

    def _start(self):
        self.ws.run_forever()

    def handle_message(self, message):
        messages, partial = self.parse_sockjs(message.data)

        for message in messages:
            self.on_message(message)

    def _close(self):
        self.ws.close()
