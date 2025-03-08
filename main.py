import json
import logging
import time

from pycrescolib.clientlib import clientlib
from dataplane_test import DataplaneTest

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

        stream_name = "stunnel_id is NOT NULL and type is NOT NULL"
        # Create dataplane with callbacks
        dp = client.get_dataplane(
            stream_name,
            text_callback,
            binary_callback
        )
        dp.connect()
        while True:
            time.sleep(1)

        '''
        # Create and run DataplaneTest with the connected client
        dataplane_tester = DataplaneTest(client, logger)
        success = dataplane_tester.run_test(num_messages=100, delay=0.1)

        if success:
            logger.info("Dataplane test completed successfully")
        else:
            logger.error("Dataplane test failed")
        '''

    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        # Always close the client when done
        logger.info("Closing Cresco connection")
        client.close()
else:
    logger.error("Failed to connect to Cresco server")