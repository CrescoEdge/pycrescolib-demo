import logging
import uuid

from pycrescolib.clientlib import clientlib
from stunnel_cadl import StunnelCADL
from stunnel_direct import StunnelDirect

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

# Connection parameters
host = 'localhost'
port = 8282
service_key = 'a6f7f889-2500-46d3-9484-5b6499186456'

# Connect to Cresco
client = clientlib(host, port, service_key)
if client.connect():

    try:
        logger.info(f"Connected to Cresco at {host}:{port}")

        # Get global region and agent
        global_region = client.api.get_global_region()
        global_agent = client.api.get_global_agent()
        logger.info(f"Global region: {global_region}, Global agent: {global_agent}")

        # Initialize the tunnel testers
        stunnel_direct_tester = StunnelDirect(client, logger)
        stunnel_cadl_tester = StunnelCADL(client, logger)

        # Example 1: Create a tunnel using existing system plugins
        stunnel_id_1 = str(uuid.uuid1())
        stunnel_direct_tester.create_tunnel(stunnel_id_1, global_region, global_agent, '2222',
                                     global_region, 'agent-controller', '192.168.4.249', '2221',
                                     '8192')

        '''
        # Example 2: Create a tunnel using CADL deployment
        stunnel_id_2 = str(uuid.uuid1())
        stunnel_cadl_tester.create_tunnel(stunnel_id_2, global_region, global_agent, '3333',
                                     global_region, global_agent, '192.168.4.249', '3331',
                                     '8192')
        '''

    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        # Always close the client when done
        logger.info("Closing Cresco connection")
        client.close()
else:
    logger.error("Failed to connect to Cresco server")