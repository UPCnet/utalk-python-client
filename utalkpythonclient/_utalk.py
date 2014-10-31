import json
import random
import re
import requests
import string
import websocket

from utalkpythonclient._stomp import StompClient


def random_str(length):
    letters = string.ascii_lowercase + string.digits
    return ''.join(random.choice(letters) for c in range(length))


class MaxAuthMixin():

    @staticmethod
    def oauth2_headers(username, token, scope="widgetcli"):
        """
        """
        headers = {
            'X-Oauth-Token': str(token),
            'X-Oauth-Username': str(username),
            'X-Oauth-Scope': str(scope),
        }
        return headers

    @staticmethod
    def get_max_info(maxserver):
        response = requests.get('{}/info'.format(maxserver), verify=False)
        info = response.json()
        return info

    @staticmethod
    def get_max_domain(maxserver):
        match = re.match(r'^.*?\/([^\/\.]+)/?$', maxserver.strip(), re.IGNORECASE)
        domain = match.groups()[0] if match else None
        return domain

    @classmethod
    def get_max_settings(cls, maxserver, username, token):
        response = requests.get(
            '{}/info/settings'.format(maxserver),
            headers=cls.oauth2_headers(username, token),
            verify=False)
        info = response.json()
        return info

    @classmethod
    def get_token(cls, oauth_server, username, password):

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

    def __init__(self, maxserver, username, password):

        max_info = self.get_max_info(maxserver)
        oauth_server = max_info['max.oauth_server']
        stomp_server = '{}/stomp'.format(maxserver.replace('http', 'ws'))

        token = self.get_token(oauth_server, username, password)
        self.domain = self.get_max_domain(maxserver)

        self.host = stomp_server
        self.username = username
        self.passcode = token
        self.stomp = StompClient(self.domain, self.username, self.passcode, self)
        print username, token

    def connect(self):
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

    def on_message(self, ws, message):
        if message[0] == 'o':
            self.stomp.connect()
        if message[0] == 'a':
            command, params, body = re.search(r'a\[\"(\w+)\\n(.*)\\n([^\n]+)"\]', message).groups()
            headers = dict(re.findall(r'([^:]+):(.*?)\\n?', params, re.DOTALL | re.MULTILINE))

            if command == 'CONNECTED':
                self.stomp.subscribe()
            if command == 'MESSAGE':
                decoded_message = json.loads(body.replace('\\"', '"').replace('\u0000', ''))
                self.stomp.receive(headers, decoded_message)
            if command == 'ERROR':
                print params, body

    def on_error(self, ws, error):
        print '> ERROR {}'.format(error)

    def on_close(self, ws):
        print "> Closed websocket connection"

    def on_open(self, ws):
        print '> Opened websocket connection to {}'.format(self.url)
