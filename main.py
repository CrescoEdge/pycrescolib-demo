import json
import logging
import time
import uuid

from dataplane_test import DataplaneTest
from pycrescolib.clientlib import clientlib
from stunnel_test import STunnelTest

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()


def text_callback(message):
    """Callback for handling text messages from the dataplane"""
    try:
        # Try to parse as JSON for better formatting
        try:
            #logger.info("Received text message from dataplane:", message)
            json_msg = json.loads(message)
            logger.info(f"Text message (JSON): {json.dumps(json_msg, indent=2)}")
        except json.JSONDecodeError:
            # Not JSON, log as plain text
            logger.info(f"Text message: {message}")
    except Exception as e:
        logger.error(f"Error in text callback: {e}")


def binary_callback(data):
    """Callback for handling binary messages from the dataplane"""
    try:
        logger.info(f"Binary data received: {len(data)} bytes")


    except Exception as e:
       logger.error(f"Error in binary callback: {e}")

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

        stunnel_tester = STunnelTest(client, logger)

        # Example 1: Create a tunnel using existing system plugins

        stunnel_id_1 = str(uuid.uuid1())
        stunnel_tester.create_tunnel(stunnel_id_1, global_region, global_agent, '2222',
                                     global_region, global_agent, '192.168.4.249', '2221',
                                     '8192', use_existing_plugins=True)
        '''
        # Example 2: Create a tunnel using CADL deployment
        stunnel_id_2 = str(uuid.uuid1())
        stunnel_tester.create_tunnel(stunnel_id_2, global_region, global_agent, '4444',
                                     global_region, global_agent, '192.168.4.249', '4441',
                                     '8192', use_existing_plugins=False)
        '''


    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        # Always close the client when done
        logger.info("Closing Cresco connection")
        client.close()
else:
    logger.error("Failed to connect to Cresco server")