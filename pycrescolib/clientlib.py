"""
Client library for Cresco framework interaction.
Improved to ensure proper WebSocket initialization and event loop management.
"""
import ssl
import logging
import asyncio
import time
import threading
import concurrent.futures
from typing import Optional, Dict, Any, Callable
from contextlib import contextmanager

from .admin import admin
from .agents import agents
from .api import api
from .dataplane import dataplane
from .globalcontroller import globalcontroller
from .logstreamer import logstreamer
from .messaging import messaging_sync as messaging
from .wc_interface import ws_interface

# Setup logging
logger = logging.getLogger(__name__)


# Configure logging for the library
def configure_logging(level=logging.INFO):
    """Configure logging for the library.

    Args:
        level: Logging level
    """
    logger = logging.getLogger('pycrescolib')
    logger.setLevel(level)

    # Add console handler if none exists
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)


# SSL Configuration helper
def setup_ssl_context(verify=False):
    """Setup SSL context.

    Args:
        verify: Whether to verify SSL certificates

    Returns:
        Configured SSL context
    """
    context = ssl.create_default_context()

    if not verify:
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        logger.warning("SSL certificate verification disabled")

    return context


class clientlib:
    """Client library for interacting with Cresco framework."""

    def __init__(self, host: str, port: int, service_key: str, verify_ssl: bool = False):
        """Initialize the client library.

        Args:
            host: Host address
            port: Port number
            service_key: Service key for authentication
            verify_ssl: Whether to verify SSL certificates
        """
        self.host = host
        self.port = port
        self.service_key = service_key
        self.verify_ssl = verify_ssl
        self._lock = threading.RLock()  # Reentrant lock for thread safety
        self._dataplanes = []  # Track active dataplanes
        self._logstreamers = []  # Track active logstreamers

        # Configure SSL handling globally if needed
        if not verify_ssl:
            self._configure_global_ssl()

        # Create WebSocket interface first - it will create its own event loop
        self.ws_interface = ws_interface()

        # Setup components with the WebSocket interface after it's initialized
        self.messaging = messaging(self.ws_interface)
        self.agents = agents(self.messaging)
        self.admin = admin(self.messaging)
        self.api = api(self.messaging)
        self.globalcontroller = globalcontroller(self.messaging)

        logger.info(f"Clientlib initialized for {host}:{port}")

    def _configure_global_ssl(self):
        """Configure global SSL settings when verification is disabled."""
        try:
            # Create unverified context
            _unverified_context = ssl._create_unverified_context()
            # Apply globally
            ssl._create_default_https_context = lambda: _unverified_context
            logger.warning("SSL certificate verification disabled globally")
        except AttributeError:
            logger.warning("Could not configure global SSL verification settings")

    def connect(self) -> bool:
        """Connect to the WebSocket server.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Reset the messaging connection state if method exists
            if hasattr(self.messaging, 'reset_connection_state'):
                self.messaging.reset_connection_state()

            ws_url = f'wss://{self.host}:{self.port}/api/apisocket'

            # Connect using the WebSocket interface
            connection_result = self.ws_interface.connect(ws_url, self.service_key, self.verify_ssl)

            if connection_result:
                # Sleep briefly to ensure connection is fully established
                time.sleep(0.5)

                # Verify the connection is working properly
                if self.ws_interface.connected():
                    logger.info("Connection verified successfully")
                    return True
                else:
                    logger.warning("Connection reported success but verification failed")
                    return False
            else:
                logger.warning("Connection attempt failed")
                return False
        except Exception as e:
            logger.error(f"Connection error: {e}")
            return False

    def connected(self) -> bool:
        """Check if connected to the WebSocket server.

        Returns:
            True if connected, False otherwise
        """
        try:
            return self.ws_interface.connected()
        except Exception as e:
            logger.error(f"Error checking connection status: {e}")
            return False

    def close(self):
        """Close the WebSocket connection and clean up resources."""
        logger.info("Closing clientlib connection and resources")

        # Close all tracked dataplanes
        for dp in self._dataplanes:
            try:
                dp.close()
            except Exception as e:
                logger.error(f"Error closing dataplane: {e}")
        self._dataplanes = []

        # Close all tracked logstreamers
        for ls in self._logstreamers:
            try:
                ls.close()
            except Exception as e:
                logger.error(f"Error closing logstreamer: {e}")
        self._logstreamers = []

        # Close WebSocket interface
        if self.ws_interface:
            try:
                self.ws_interface.close()
            except Exception as e:
                logger.error(f"Error closing WebSocket interface: {e}")

    def get_dataplane(self, stream_name: str, callback: Optional[Callable] = None) -> dataplane:
        # Create dataplane with the same service key used by clientlib
        dp = dataplane(self.host, self.port, stream_name, self.service_key, callback)
        logger.debug(f"Created dataplane for stream: {stream_name}")
        # Track for cleanup
        self._dataplanes.append(dp)
        return dp

    def get_logstreamer(self, callback: Optional[Callable] = None) -> logstreamer:
        # Create logstreamer with the same service key used by clientlib
        ls = logstreamer(self.host, self.port, self.service_key, callback)
        logger.debug("Created logstreamer")
        # Track for cleanup
        self._logstreamers.append(ls)
        return ls

    @contextmanager
    def connection(self):
        """Context manager for client connections.

        Yields:
            The client instance
        """
        connection_successful = False
        try:
            # Attempt to connect
            connection_successful = self.connect()
            if not connection_successful:
                raise ConnectionError("Failed to connect to Cresco server")

            # Connection succeeded, yield the client
            yield self
        finally:
            # Always close the connection when exiting the context
            if connection_successful:
                self.close()