
class api(object):

    def __init__(self, messaging):
        self.messaging = messaging
        self.global_region = None
        self.global_agent = None

    def get_api_region_name(self):
        return self.messaging.get_region()

    def get_api_agent_name(self):
        return self.messaging.get_agent()

    def get_api_plugin_name(self):
        return self.messaging.get_plugin()

    def get_global_region(self):
        if (self.global_region is None):
            self.get_global_info()

        return self.global_region

    def get_global_agent(self):
        if(self.global_agent is None):
            self.get_global_info()

        return self.global_agent

    def get_global_info(self):
        message_event_type = 'EXEC'
        message_payload = dict()
        message_payload['action'] = 'globalinfo'

        reply = self.messaging.plugin_msgevent(True, message_event_type, message_payload, self.get_api_plugin_name())
        self.global_region = reply['global_region']
        self.global_agent = reply['global_agent']
