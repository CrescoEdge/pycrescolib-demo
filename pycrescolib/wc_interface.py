import ssl

from websocket import create_connection

class ws_interface(object):

    def __init__(self):
        self.url = None
        self.ws = None

    def connect(self, url):
        self.url = url
        self.ws = create_connection(self.url, sslopt={"cert_reqs": ssl.CERT_NONE}, header={'cresco_service_key': 'c988701a-5f2a-43ac-b915-156049c5d1ee'})
        return self.ws.connected

    def connected(self):
        if self.ws is None:
            return False
        else:
            return self.ws.connected

    def close(self):
        if self.ws is not None:
            self.ws.close()
