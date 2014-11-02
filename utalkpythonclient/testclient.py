from utalkpythonclient.client import UTalkClient
from gevent.monkey import patch_all
import gevent
from ws4py.client.geventclient import WebSocketClient


class UTalkTestClient(UTalkClient):
    ws_client_class = WebSocketClient

    def setup(self, send, expect, ready):
        """
            Configures the test
        """
        self.to_send = send
        self.to_expect = expect
        self.wait_send = ready

        self.expected_messages = len(self.to_expect) + len(self.to_send)
        self.expected_acks = self.expected_messages
        self.received_messages = 0
        self.ackd_messages = 0

    def loop(self):
        while True:
            self.ws.receive()

    def on_connecting(self):
        patch_all()

    def on_message_received(self):
        self.received_messages += 1
        self.test_finished()

    def on_frame(self):
        gevent.sleep()

    def on_message_ackd(self):
        self.ackd_messages += 1
        self.test_finished()

    def test_finished(self):
        print '{} AKCD:{}, RECV:{}'.format(self.username, self.ackd_messages, self.received_messages)
        if self.received_messages == self.expected_messages and \
           self.ackd_messages == self.expected_acks:
            self.disconnect()

    def on_start_listening(self):
        self.wait_send.ready()
        gevent.sleep(1)
        self.wait_send.event.get()

        self.log("start sending {} messages".format(self.username))
        for conversation_id, text in self.to_send:
            gevent.sleep()
            self.send_message(conversation_id, text)

    def teardown(self):
        """
            Unpatches sockets
        """
        import socket
        reload(socket)
