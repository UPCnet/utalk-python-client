from utalkpythonclient.client import UTalkClient
from gevent.monkey import patch_all
import gevent
from datetime import datetime, timedelta


class UTalkTestClient(UTalkClient):

    def setup(self, conversation, send, expect, ready, start_delay=0, message_delay=0):
        """
            Configures the test
        """
        self.to_send = send
        self.wait_send = ready
        self.conversation = conversation
        self.start_delay = start_delay
        self.message_delay = message_delay

        self.expected_messages = send + expect
        self.expected_acks = send + expect

        self.received_messages = 0
        self.ackd_messages = 0
        self.stats = {
            "recv_times": [],
            "ackd_times": [],
            "send_times": []
        }

    def succeded(self):
        return self.received_messages >= self.expected_messages and \
            self.ackd_messages >= self.expected_acks

    # def on_connecting(self):
    #     patch_all()

    def on_message_received(self, message):
        # Collect stats for messages received from other users
        if self.username != message.json['u']['u']:
            now = datetime.utcnow()
            sent = datetime.strptime(message.json['p'], '%Y-%m-%dT%H:%M:%S.%fZ')
            self.stats['recv_times'].append((sent, now))
        else:
            self.stats['send_times'].append(datetime.strptime(message.json['p'], '%Y-%m-%dT%H:%M:%S.%fZ'))

        self.received_messages += 1
        self.test_finished()

    def on_message(self):
        gevent.sleep()

    def on_message_ackd(self, message):
        if self.username != message.json['u']['u']:
            now = datetime.utcnow()
            sent = datetime.strptime(message.json['p'], '%Y-%m-%dT%H:%M:%S.%fZ')
            self.stats['ackd_times'].append((sent, now))

        self.ackd_messages += 1
        self.test_finished()

    def test_finished(self):
        #print '{} AKCD:{}, RECV:{}'.format(self.username, self.ackd_messages, self.received_messages)
        if self.succeded():
            self.disconnect()

    @property
    def messages(self):
        """
            Generates numbered messages
        """
        for i in range(self.to_send):
            yield (self.conversation, 'This is Message {} from {}'.format(i, self.username))

    def on_start_listening(self):
        self.wait_send.ready()
        gevent.sleep()
        self.wait_send.event.get()
        gevent.sleep(self.start_delay)

        self.log("start sending {} messages".format(self.username))
        next_message_date = datetime.utcnow()
        for conversation_id, text in self.messages:
            while datetime.utcnow() <= next_message_date:
                gevent.sleep()
            self.send_message(conversation_id, text)
            next_message_date = datetime.utcnow() + timedelta(seconds=self.message_delay)

    def teardown(self):
        """
            Unpatches sockets
        """
        import socket
        reload(socket)
