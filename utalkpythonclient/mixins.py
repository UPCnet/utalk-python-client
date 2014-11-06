import json
import re
import requests


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
