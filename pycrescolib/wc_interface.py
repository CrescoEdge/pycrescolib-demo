import ssl
from cryptography import x509

from websocket import create_connection

class ws_interface(object):

    def __init__(self):
        self.url = None
        self.ws = None
        self.region = None
        self.agent = None
        self.plugin = None

    def connect(self, url, service_key):
        self.url = url
        surl = self.url.split('/')[2].split(':')

        self.ws = create_connection(self.url, sslopt={"cert_reqs": ssl.CERT_NONE}, header={'cresco_service_key': service_key})

        serverAddress = (surl[0], surl[1])
        pem_data = ssl.get_server_certificate(serverAddress)
        #certificate = x509.load_pem_x509_certificate(cert)
        cert = x509.load_pem_x509_certificate(str.encode(pem_data))

        ident_string = cert.subject.rfc4514_string().replace('CN=','').split('_')

        self.region = ident_string[0]
        self.agent = ident_string[1]
        self.plugin = ident_string[2]

        return self.ws.connected


    def connected(self):
        if self.ws is None:
            return False
        else:
            return self.ws.connected

    def close(self):
        if self.ws is not None:
            self.ws.close()

    def get_region(self):
        return self.region

    def get_agent(self):
        return self.agent

    def get_plugin(self):
        return self.plugin

    def get_cert(self, host, port):
        """Gets the certificate from a remote server.

        Args:
            host: The hostname of the remote server.
            port: The port of the remote server.

        Returns:
            The certificate from the remote server.
        """

        context = ssl.create_default_context()
        context.check_hostname = True
        context.verify_mode = ssl.CERT_REQUIRED

        conn = context.wrap_socket(ssl.SOCK_STREAM, host, port)
        conn.close()

        return context.get_peer_certificate()

