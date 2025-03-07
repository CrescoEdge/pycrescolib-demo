import json
import time
import logging

from pycrescolib.clientlib import clientlib

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

# Connection parameters
host = 'localhost'
port = 8282
service_key = 'a6f7f889-2500-46d3-9484-5b6499186456'


# Create a dataplane message callback
def dataplane_callback(message):
    try:
        # Try to parse as JSON for better formatting
        try:
            json_msg = json.loads(message)
            logger.info(f"Dataplane message (JSON): {json.dumps(json_msg, indent=2)}")
        except json.JSONDecodeError:
            # Not JSON, log as plain text
            logger.info(f"Dataplane message: {message}")
    except Exception as e:
        logger.error(f"Error in dataplane callback: {e}")


# Connect to Cresco
client = clientlib(host, port, service_key)
if client.connect():
    try:
        logger.info(f"Connected to Cresco at {host}:{port}")

        # Get global region and agent
        global_region = client.api.get_global_region()
        global_agent = client.api.get_global_agent()
        logger.info(f"Global region: {global_region}, Global agent: {global_agent}")

        # Create and connect to dataplane
        stream_name = "region_id IS NOT NULL AND agent_id IS NOT NULL"  # Use appropriate stream name
        dp = client.get_dataplane(stream_name, callback=dataplane_callback)

        if dp.connect():
            logger.info(f"Successfully connected to dataplane stream: {stream_name}")

            # Wait a moment for the connection to stabilize
            time.sleep(2)

            # Send a test message
            test_message = {"type": "test", "message": "Hello from Python client", "timestamp": time.time()}
            dp.send(json.dumps(test_message))
            logger.info(f"Sent test message to stream: {stream_name}")

            # Keep running and receiving messages
            logger.info("Waiting for dataplane messages (30 seconds)...")
            time.sleep(30)
        else:
            logger.error(f"Failed to connect to dataplane stream: {stream_name}")

    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        # Always close the client when done
        logger.info("Closing Cresco connection")
        client.close()
else:
    logger.error("Failed to connect to Cresco server")