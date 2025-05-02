import json
import time
import logging

class DataplaneTest:
    def __init__(self, client, logger=None):
        """
        Initialize the DataplaneTest class with a Cresco client

        Args:
            client: A connected pycrescolib clientlib instance
            logger: Optional logger instance (will create one if not provided)
        """
        # Store the client reference
        self.client = client
        self.dp = None

        # Setup logging if not provided
        if logger:
            self.logger = logger
        else:
            logging.basicConfig(level=logging.INFO)
            self.logger = logging.getLogger(__name__)

    def text_callback(self, message):
        """Callback for handling text messages from the dataplane"""
        try:
            # Try to parse as JSON for better formatting
            try:
                json_msg = json.loads(message)
                self.logger.info(f"Text message (JSON): {json.dumps(json_msg, indent=2)}")
            except json.JSONDecodeError:
                # Not JSON, log as plain text
                self.logger.info(f"Text message: {message}")
        except Exception as e:
            self.logger.error(f"Error in text callback: {e}")

    def binary_callback(self, data):
        """Callback for handling binary messages from the dataplane"""
        try:
            self.logger.info(f"Binary data received: {len(data)} bytes")

            # You could process the binary data according to your needs
            # For example, if it's an image, save it:
            # with open("received_image.jpg", "wb") as f:
            #     f.write(data)

            # Or if it's UTF-8 text in binary form, you could decode it:
            try:
                text = data.decode('utf-8')
                self.logger.info(f"Binary data decoded as UTF-8: {text[:100]}...")
            except UnicodeDecodeError:
                self.logger.info("Binary data is not valid UTF-8")

        except Exception as e:
            self.logger.error(f"Error in binary callback: {e}")

    def setup_dataplane(self):
        """Configure and create the dataplane connection"""
        dp_config = dict()
        dp_config['ident_key'] = "stream_name"
        dp_config['ident_id'] = "1234"
        dp_config['io_type_key'] = "type"
        dp_config['output_id'] = "output"
        dp_config['input_id'] = "output"

        # Create dataplane configuration
        stream_name = json.dumps(dp_config)

        # Create dataplane with callbacks
        self.dp = self.client.get_dataplane(
            stream_name,
            self.text_callback,
            self.binary_callback
        )

        return stream_name

    def run_test(self, num_messages=100, delay=0.1):
        """
        Run the dataplane test by sending a series of messages

        Args:
            num_messages: Number of messages to send (default: 100)
            delay: Delay between messages in seconds (default: 0.1)

        Returns:
            bool: True if test completed successfully, False otherwise
        """
        # Setup dataplane
        stream_name = self.setup_dataplane()

        # Connect dataplane
        if self.dp.connect():
            self.logger.info(f"Successfully connected to dataplane stream: {stream_name}")

            # Wait a moment for the connection to stabilize
            time.sleep(2)

            # Send messages in a loop
            self.logger.info(f"Starting to send {num_messages} messages...")

            for i in range(num_messages):
                # Create a message with counter
                message = {
                    "type": "test",
                    "message": f"Message #{i + 1} of {num_messages}",
                    "timestamp": time.time()
                }

                # Send as text message (JSON)
                self.dp.send(json.dumps(message))

                # Alternate between text and binary every 10 messages
                if i % 10 == 5:
                    # Send binary message
                    binary_data = f"Binary message #{i + 1} of {num_messages}".encode('utf-8')
                    self.dp.send_binary(binary_data)
                    self.logger.info(f"Sent binary message #{i + 1}")
                else:
                    self.logger.info(f"Sent text message #{i + 1}")

                # Small delay to avoid overwhelming the connection
                time.sleep(delay)

            self.logger.info(f"Finished sending {num_messages} messages")

            # Wait a bit to ensure all messages are processed
            self.logger.info("Waiting for 5 seconds to ensure all messages are processed...")
            time.sleep(5)

            return True
        else:
            self.logger.error(f"Failed to connect to dataplane stream: {stream_name}")
            return False