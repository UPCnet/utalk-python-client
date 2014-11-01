import json
import random
import re
import requests
import string
import websocket

from collections import namedtuple
from maxcarrot import RabbitMessage
from utalkpythonclient._stomp import StompHelper


def random_str(length):
    letters = string.ascii_lowercase + string.digits
    return ''.join(random.choice(letters) for c in range(length))


SOCKJS_CONNECTED = object()
SOCKJS_MESSAGE = object()
SOCKJS_HEARTBEAT = object()
SOCKJS_UNKNOWN = object()

SOCKJS_TYPES = {
    'o': SOCKJS_CONNECTED,
    'h': SOCKJS_HEARTBEAT,
    'a': SOCKJS_MESSAGE
}

Message = namedtuple('Message', ['type', 'content'])


class MaxAuthMixin():
    """
        Helper functions for max/oauth authentication tasks
    """

    @staticmethod
    def oauth2_headers(username, token, scope="widgetcli"):
        """
            Returns valid OAuth2 authentication headers for max.
        """
        headers = {
            'X-Oauth-Token': str(token),
            'X-Oauth-Username': str(username),
            'X-Oauth-Scope': str(scope),
        }
        return headers

    @staticmethod
    def get_max_info(maxserver):
        """
            Returns the public info bits from a maxserver.
        """
        response = requests.get('{}/info'.format(maxserver), verify=False)
        info = response.json()
        return info

    @classmethod
    def get_max_settings(cls, maxserver, username, token):
        """
            Returns the (private) settings from a maxserver.
        """
        response = requests.get(
            '{}/info/settings'.format(maxserver),
            headers=cls.oauth2_headers(username, token),
            verify=False)
        info = response.json()
        return info

    @staticmethod
    def get_max_domain(maxserver):
        """
            Extracts the domain from the max server url, if any.
        """
        match = re.match(r'^.*?\/([^\/\.]+)/?$', maxserver.strip(), re.IGNORECASE)
        domain = match.groups()[0] if match else None
        return domain

    @classmethod
    def get_token(cls, oauth_server, username, password):
        """
            Retrieves the token for an authenticated user.
        """

        payload = {
            "grant_type": 'password',
            "client_id": 'MAX',
            "scope": 'widgetcli',
            "username": username,
            "password": password
        }
        resp = requests.post('{0}/token'.format(oauth_server), data=payload, verify=False)
        response = json.loads(resp.text)

        if resp.status_code == 200:
            # Get token, falling back to legacy oauth server
            token = response.get(
                "access_token",
                response.get(
                    "oauth_token",
                    None
                )
            )
            return token

        elif resp.status_code in [400, 401]:
            raise Exception('{error}: {error_description}'.format(**response))


class UTalkClient(object, MaxAuthMixin):

    def __init__(self, maxserver, username, password, quiet=False):
        """
            Creates a utalk client fetching required info from the
            max server.
        """
        self.quiet = quiet
        max_info = self.get_max_info(maxserver)
        oauth_server = max_info['max.oauth_server']
        stomp_server = '{}/stomp'.format(maxserver.replace('http', 'ws'))

        self.host = stomp_server
        self.domain = self.get_max_domain(maxserver)
        self.username = username
        self.login = username if self.domain is None else '{}:{}'.format(self.domain, username)
        self.token = self.get_token(oauth_server, username, password)

        self.stomp = StompHelper()

    def log(self, message):
        if not self.quiet:
            print message

    def trigger(self, event, *args, **kwargs):
        """
            Tries to call a method binded to an event
        """
        event_handler_name = 'on_{}'.format(event)
        if hasattr(self, event_handler_name):
            getattr(self, event_handler_name)(*args, **kwargs)

    def send(self, message):
        """
            Wraps a message to a valid sockjs frame
        """
        wrapped = '["{}"]'.format(message)
        self.ws.send(wrapped)
        return wrapped

    @staticmethod
    def parse_sockjs(frame):
        """
            Parses a sockjs frame and extracts it's content.
        """
        match = re.search(r'([aoh]){1}(?:\[\")*(.*?)(?:[\]"])*$', frame).groups()
        if match:
            wstype, content = match
            return Message(SOCKJS_TYPES[wstype], content)
        else:
            return Message(SOCKJS_UNKNOWN, '')

    def connect(self):
        """
            Opens a websocket and loops waiting for incoming frames.
        """
        self.trigger('connecting')
        self.url = '/'.join([
            self.host,
            str(random.randint(0, 1000)),
            random_str(8),
            'websocket'])
        self.ws = websocket.WebSocketApp(
            self.url,
            header={'Connection': 'Keep-Alive'},
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )
        self.ws.on_open = self.on_open
        self.ws.run_forever()

    def disconnect(self):
        """
            Disconnects client from socket
        """
        self.ws.close()

    def on_message(self, ws, frame):
        """
            Triggered when a frame arribes trough the websocket.

            Decodes contained stomp frame, and handles actions.
        """
        message = self.parse_sockjs(frame)

        if message.type is SOCKJS_CONNECTED:
            self.send(self.stomp.connect_frame(self.login, self.token))
            self.log('> Started stomp session as {}'.format(self.username))

        elif message.type is SOCKJS_MESSAGE:
            stomp_message = self.stomp.decode(message.content)

            if stomp_message.command == 'CONNECTED':
                destination = "/exchange/{}.subscribe".format(self.username)
                self.send(self.stomp.subscribe_frame(destination))
                self.log('> Listening on {} messages'.format(self.username))
                self.trigger('start_listening')

            if stomp_message.command == 'MESSAGE':
                self.handle_message(stomp_message)
            if stomp_message.command == 'ERROR':
                self.log(message.content)

    def send_message(self, conversation, text):
        """
            Sends a stomp message to a specific conversation
        """
        message = RabbitMessage()
        message.prepare()
        message['source'] = 'test'
        message['data'] = {'text': text}
        message['action'] = 'add'
        message['object'] = 'message'
        message['user'] = {'username': self.username}
        if self.domain:
            message['domain'] = self.domain

        headers = {
            "destination": "/exchange/{}.publish/{}.messages".format(self.username, conversation),
        }
        # Convert json to text without blank space, and escape it
        json_message = json.dumps(message.packed, separators=(',', ':'))
        json_message = json_message.replace('"', '\\"')

        self.send(self.stomp.send_frame(headers, json_message))
        self.trigger('message_sent')

    def handle_message(self, stomp):
        """
            Handle a decoded stomp message and log them.
        """
        message = RabbitMessage.unpack(stomp.json)
        destination = re.search(r'([0-9a-f]+).(?:notifications|messages)', stomp.headers['destination']).groups()[0]
        if message['action'] == 'add' and message['object'] == 'message':
            self.log('> {}@{}: {}'.format(message['user']['username'], destination, message['data']['text']))
            self.trigger('message_received')
        if message['action'] == 'add' and message['object'] == 'conversation':
            self.log('> {}@{}: Just started a chat'.format(message['user']['username'], destination))
            self.trigger('conversation_started')

    def on_error(self, ws, error):
        """
            Logs on websocket error event
        """
        self.log('> ERROR {}'.format(error))

    def on_close(self, ws):
        """
            Logs on websocket close event
        """
        self.log("> Closed websocket connection")

    def on_open(self, ws):
        """
            Logs on websocket opened event
        """
        self.log('> Opened websocket connection to {}'.format(self.url))
