"""UTalk Websocket client

Usage:
    utalk <maxserver> <username>

Options:
"""

from docopt import docopt
from utalkpythonclient._utalk import UTalkClient
import getpass
import sys


def main(argv=sys.argv):

    arguments = docopt(__doc__, version='UTalk websocket client 1.0')

    print
    print "  UTalk websocket client"
    print

    print '> Enter password for user {}'.format(arguments['<username>'])
    password = getpass.getpass()

    client = UTalkClient(
        maxserver=arguments['<maxserver>'],
        username=arguments['<username>'],
        password=password
    )
    client.connect()