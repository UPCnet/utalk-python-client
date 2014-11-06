import json
import re

from maxcarrot import RabbitMessage
from utalkpythonclient._stomp import StompHelper

from utalkpythonclient.mixins import MaxAuthMixin
from utalkpythonclient.transports import XHRPollingTransport
from utalkpythonclient.transports import WebsocketTransport
from utalkpythonclient.transports import SOCKJS_CONNECTED
from utalkpythonclient.transports import SOCKJS_MESSAGE
from utalkpythonclient.transports import SOCKJS_UNKNOWN
from utalkpythonclient.transports import SOCKJS_HEARTBEAT


class UTalkClient(object, MaxAuthMixin):
    Transport = XHRPollingTransport

    def __init__(self, maxserver, username, password, quiet=False):
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
        self.transport = self.Transport(maxserver, 'stomp')

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
        self.transport.send(message)

    def start(self):
        try:
            self.transport.start()
        except KeyboardInterrupt:
            self.log('\n> User interrupted')
            self.disconnect()
        return False

    def connect(self):
        """
            Opens a websocket and loops waiting for incoming frames.
        """
        self.trigger('connecting')
        self.transport.on_message = self.on_message
        self.transport.on_open = self.on_open
        self.transport.on_close = self.on_close
        self.transport.connect()

    def disconnect(self):
        """
            Disconnects client from socket
        """
        self.log('> Closing communication')
        self.transport.close()

    def on_message(self, message):
        """
            Triggered when a frame arribes trough the websocket.

            Decodes contained stomp frame, and handles actions.
        """
        self.trigger('frame')
        if message.type is SOCKJS_CONNECTED:
            self.send(self.stomp.connect_frame(self.login, self.token))
            self.log('> Started stomp session as {}'.format(self.username))

        elif message.type is SOCKJS_HEARTBEAT:
            pass

        elif message.type is SOCKJS_MESSAGE:
            try:
                stomp_message = self.stomp.decode(message.content)
            except:
                print 'decode error'
            else:
                if stomp_message.command == 'CONNECTED':
                    destination = "/exchange/{}.subscribe".format(self.username)
                    self.send(self.stomp.subscribe_frame(destination))
                    self.log('> Listening on {} messages'.format(self.username))
                    self.trigger('start_listening')

                elif stomp_message.command == 'MESSAGE':
                    self.handle_message(stomp_message)

                elif stomp_message.command == 'ERROR':
                    self.log(message.content)

                else:
                    self.log(stomp_message)

        elif message.type is SOCKJS_UNKNOWN:
            print message

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
        elif message['action'] == 'add' and message['object'] == 'conversation':
            self.log('> {}@{}: Just started a chat'.format(message['user']['username'], destination))
            self.trigger('conversation_started')
        elif message['action'] == 'ack' and message['object'] == 'message':
            self.trigger('message_ackd')
        else:
            print '\n{}\n'.format(message)

    def on_error(self, ws, error):
        """
            Logs on websocket error event
        """
        self.log('> ERROR {}'.format(error))

    def on_close(self, ws, unk):
        """
            Logs on websocket close event
        """
        print ws
        print unk
        self.log("> Closed websocket connection")

    def on_open(self):
        """
            Logs on websocket opened event
        """
        self.log('> Opened websocket connection to {}'.format(self.transport.url))
