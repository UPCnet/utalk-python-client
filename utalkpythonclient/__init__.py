"""UTalk Websocket client

Usage:
    utalk <maxserver> <username> [options]

Options:
    -p <password>, --password <password>            Password for the utalk user
    -l <token>, --tokenlogin <token>                Login with token instead of password
    -u <utalkserver>, --utalkserver <utalkserver>   Url of the sockjs endpoint
    -t <transport>, --transport                     Transport used, can be websocket, xhr, xhr_streaming [default: websocket]
"""

from docopt import docopt
from utalkpythonclient.client import UTalkClient
import getpass
import sys


def main(argv=sys.argv):

    arguments = docopt(__doc__, version='UTalk websocket client 1.0')

    print
    print "  UTalk client"
    print

    password = arguments.get('--password', None)
    token = arguments.get('--tokenlogin', None)
    if not password and not token:
        print '> Enter password for user {}'.format(arguments['<username>'])
        password = getpass.getpass()

    params = dict(
        maxserver=arguments['<maxserver>'],
        username=arguments['<username>'],
        transport=arguments['--transport']
    )

    if password:
        params['password'] = password
    elif token:
        params['token_login'] = token

    if arguments.get('--utalkserver>', None):
        params['utalkserver'] = arguments.get('--utalkserver')

    client = UTalkClient(**params)
    client.start()
