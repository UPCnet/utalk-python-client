from utalkpythonclient.client import UTalkClient
from gevent.monkey import patch_all
import gevent


class UTalkTestClient(UTalkClient):

    def setup(self, conversation, send, expect, ready):
        """
            Configures the test
        """
        self.to_send = send
        self.wait_send = ready
        self.conversation = conversation

        self.expected_messages = send + expect
        self.expected_acks = send + expect

        self.received_messages = 0
        self.ackd_messages = 0

    def succeded(self):
        return self.received_messages == self.expected_messages and \
            self.ackd_messages == self.expected_acks

    def on_connecting(self):
        patch_all()

    def on_message_received(self):
        self.received_messages += 1
        self.test_finished()

    def on_message(self):
        gevent.sleep()

    def on_message_ackd(self):
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
        gevent.sleep(1)
        self.wait_send.event.get()

        self.log("start sending {} messages".format(self.username))
        for conversation_id, text in self.messages:
            gevent.sleep()
            self.send_message(conversation_id, text)

    def teardown(self):
        """
            Unpatches sockets
        """
        import socket
        reload(socket)
