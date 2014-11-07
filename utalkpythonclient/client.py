import json
import re

from maxcarrot import RabbitMessage
from utalkpythonclient._stomp import StompHelper

from utalkpythonclient.mixins import MaxAuthMixin
from utalkpythonclient.transports import TRANSPORTS


class UTalkClient(object, MaxAuthMixin):

    def __init__(self, maxserver, username, password, quiet=False, transport=None):
        """
            Creates a utalk client fetching required info from the
            max server.
        """
        self.quiet = quiet
        max_info = self.get_max_info(maxserver)
        oauth_server = max_info['max.oauth_server']

        self.domain = self.get_max_domain(maxserver)
        self.username = username
        self.login = username if self.domain is None else '{}:{}'.format(self.domain, username)
        self.token = self.get_token(oauth_server, username, password)

        self.stomp = StompHelper()
        self.transport = self.get_transport(transport, maxserver, 'stomp')

    @staticmethod
    def get_transport(transport, *args):
        """
            Get a initialized instance of the choosen transport.

            Defaults to websocket transport
        """
        transport_class = TRANSPORTS.get(transport, TRANSPORTS.get('websocket'))
        return transport_class(*args)

    def log(self, message):
        """
            Logs application messages when not on quiet mode
        """
        if not self.quiet:
            print message

    def trigger(self, event, *args, **kwargs):
        """
            Tries to call a method binded to an event, when defined by a subclass.
            The methods MUST be named as the event, prefixed with on_
        """
        event_handler_name = 'on_{}'.format(event)
        if hasattr(self, event_handler_name):
            getattr(self, event_handler_name)(*args, **kwargs)

    def send(self, message):
        """
            Sends a message trough the transport
        """
        self.transport.send(message)

    def start(self):
        """
            Starts the transport listener
        """
        try:
            self.transport.start()
        except KeyboardInterrupt:
            self.log('\n> User interrupted')
            self.disconnect()
        return False

    def connect(self):
        """
            Initializes the transport bindings and connection
        """
        self.trigger('connecting')
        self.transport.bind(
            on_open=self.handle_open,
            on_message=self.handle_message,
            on_heartbeat=self.handle_heartbeat,
            on_close=self.handle_close
        )
        self.transport.connect()

    def disconnect(self):
        """
            Terminates transport connection
        """
        self.log('> Closing communication')
        self.transport.close()

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

    def process_message(self, stomp):
        """
            Handle a decoded stomp message.
            We're assuming that stomp messages will ever contain a MaxCarrot message.
            Based on properties fn the latter, we'll execute proper actions.
        """
        message = RabbitMessage.unpack(stomp.json)
        destination = re.search(r'([0-9a-f]+).(?:notifications|messages)', stomp.headers['destination']).groups()[0]
        if message['action'] == 'add' and message['object'] == 'message':
            self.log('> {}@{}: {}'.format(message['user']['username'], destination, message['data']['text']))
            self.trigger('message_received')
        elif message['action'] == 'add' and message['object'] == 'conversation':
            self.log('> {}@{}: Just started a chat'.format(message['user']['username'], destination))
            self.trigger('conversation_started')
        elif message['action'] == 'ack' and message['object'] == 'message':
            self.trigger('message_ackd')
        else:
            print '\n{}\n'.format(message)

    def handle_open(self):
        """
            Triggered by the transport on a succesfully opened connection.
            Tries to initialize the stomp session.
        """
        self.log('> Opened {} connection to {}'.format(self.transport.transport_id, self.transport.url))
        self.send(self.stomp.connect_frame(self.login, self.token))
        self.log('> Starting STOMP session as {}'.format(self.username))

    def handle_message(self, message):
        """
            Triggered by the transport when a message arrives
            Executes actions based on the stomp command in the message
        """
        self.trigger('message')
        stomp_message = self.stomp.decode(message.content)
        if stomp_message.command == 'CONNECTED':
            self.log('> STOMP Session succesfully started')
            destination = "/exchange/{}.subscribe".format(self.username)
            self.send(self.stomp.subscribe_frame(destination))
            self.log('> Listening on {} messages'.format(self.username))
            self.trigger('start_listening')

        elif stomp_message.command == 'MESSAGE':
            self.process_message(stomp_message)

        elif stomp_message.command == 'ERROR':
            self.log(message.content)

        else:
            self.log(stomp_message)

    def handle_heartbeat(self):
        """
            Triggered by the transport when a heartbeat  is received
        """
        self.log("> Ping!")

    def handle_close(self, reason):
        """
            Triggered by the transport when a close
        """
        self.log('> Closed {} connection. Reason: {}'.format(self.transport.transport_id, reason))
