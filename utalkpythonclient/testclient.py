from utalkpythonclient.client import UTalkClient


class UTalkTestClient(UTalkClient):

    def setup(self):
        """
            Configures the test
        """
        pass

    def connect(self):
        super(UTalkTestClient, self).connect()
