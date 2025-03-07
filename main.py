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


# Create separate callbacks for text and binary messages
def text_callback(message):
    try:
        # Try to parse as JSON for better formatting
        try:
            json_msg = json.loads(message)
            logger.info(f"Text message (JSON): {json.dumps(json_msg, indent=2)}")
        except json.JSONDecodeError:
            # Not JSON, log as plain text
            logger.info(f"Text message: {message}")
    except Exception as e:
        logger.error(f"Error in text callback: {e}")


def binary_callback(data):
    try:
        logger.info(f"Binary data received: {len(data)} bytes")

        # You could process the binary data according to your needs
        # For example, if it's an image, save it:
        # with open("received_image.jpg", "wb") as f:
        #     f.write(data)

        # Or if it's UTF-8 text in binary form, you could decode it:
        try:
            text = data.decode('utf-8')
            logger.info(f"Binary data decoded as UTF-8: {text[:100]}...")
        except UnicodeDecodeError:
            logger.info("Binary data is not valid UTF-8")

    except Exception as e:
        logger.error(f"Error in binary callback: {e}")


# Connect to Cresco
client = clientlib(host, port, service_key)
if client.connect():
    try:
        logger.info(f"Connected to Cresco at {host}:{port}")

        # Get global region and agent
        global_region = client.api.get_global_region()
        global_agent = client.api.get_global_agent()
        logger.info(f"Global region: {global_region}, Global agent: {global_agent}")

        dp_config = dict()
        dp_config['ident_key'] = "stream_name"
        dp_config['ident_id'] = "1234"
        dp_config['io_type_key'] = "type"
        dp_config['output_id'] = "output"
        dp_config['input_id'] = "output"

        # Create dataplane with both text and binary callbacks
        stream_name = json.dumps(dp_config)

        dp = client.get_dataplane(stream_name, text_callback, binary_callback)

        # Connect dataplane
        if dp.connect():
            logger.info(f"Successfully connected to dataplane stream: {stream_name}")

            # Wait a moment for the connection to stabilize
            time.sleep(2)

            # Send messages in a loop 100 times
            logger.info("Starting to send 100 messages...")

            for i in range(100):
                # Create a message with counter
                message = {
                    "type": "test",
                    "message": f"Message #{i + 1} of 100",
                    "timestamp": time.time()
                }

                # Send as text message (JSON)
                dp.send(json.dumps(message))

                # Alternate between text and binary every 10 messages
                if i % 10 == 5:
                    # Send binary message
                    binary_data = f"Binary message #{i + 1} of 100".encode('utf-8')
                    dp.send_binary(binary_data)
                    logger.info(f"Sent binary message #{i + 1}")
                else:
                    logger.info(f"Sent text message #{i + 1}")

                # Small delay to avoid overwhelming the connection
                time.sleep(0.1)

            logger.info("Finished sending 100 messages")

            # Wait a bit to ensure all messages are processed
            logger.info("Waiting for 5 seconds to ensure all messages are processed...")
            time.sleep(5)

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