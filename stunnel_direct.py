import json
import logging
from typing import Dict, List, Tuple, Optional

from pycrescolib.utils import decompress_param


class StunnelDirect:
    def __init__(self, client, logger=None):
        """
        Initialize the StunnelDirect class with a Cresco client

        Args:
            client: A connected pycrescolib clientlib instance
            logger: Optional logger instance (will create one if not provided)
        """
        # Store the client reference
        self.client = client

        # Setup logging if not provided
        if logger:
            self.logger = logger
        else:
            logging.basicConfig(level=logging.INFO)
            self.logger = logging.getLogger(__name__)



    def create_tunnel(self, stunnel_id: str, src_region: str, src_agent: str, src_port: str,
                      dst_region: str, dst_agent: str, dst_host: str, dst_port: str,
                      buffer_size: str) -> dict | None:
        """
        Create a tunnel using existing system plugins.

        Args:
            stunnel_id: A unique ID for the tunnel.
            src_region: The source region.
            src_agent: The source agent.
            src_port: The source port.
            dst_region: The destination region.
            dst_agent: The destination agent.
            dst_host: The destination host.
            dst_port: The destination port.
            buffer_size: The buffer size for the tunnel.
        """
        self.logger.info("Attempting to create tunnel using existing system plugins.")
        src_plugin_id, dst_plugin_id = self._find_existing_stunnel_plugins(src_region, src_agent, dst_region, dst_agent)

        if src_plugin_id and dst_plugin_id:
            self.logger.info(f"Found existing stunnel plugins: src_plugin_id={src_plugin_id}, dst_plugin_id={dst_plugin_id}")
            return self._configure_existing_tunnel(stunnel_id, src_region, src_agent, src_port,
                                            dst_region, dst_agent, dst_host, dst_port,
                                            buffer_size, src_plugin_id, dst_plugin_id)

        else:
            self.logger.error("PROCESS FAILED: Could not find the required existing system stunnel plugins.")
            self.logger.error("Please ensure that stunnel plugins are running on both the source and destination agents and that their names start with 'system-' or 'systems-'.")


    def _find_existing_stunnel_plugins(self, src_region: str, src_agent: str, dst_region: str, dst_agent: str) -> Tuple[
        Optional[str], Optional[str]]:
        """
        Find existing stunnel system plugins on the source and destination agents.

        This method calls the helper `_find_existing_stunnel_plugin` for each agent.

        Args:
            src_region: The source region.
            src_agent: The source agent.
            dst_region: The destination region.
            dst_agent: The destination agent.

        Returns:
            A tuple containing (src_plugin_id, dst_plugin_id).
        """
        try:
            self.logger.info("Finding stunnel plugins for source and destination agents.")
            src_plugin_id = self.find_existing_stunnel_plugin(src_region, src_agent)
            dst_plugin_id = self.find_existing_stunnel_plugin(dst_region, dst_agent)
            return src_plugin_id, dst_plugin_id
        except Exception as e:
            self.logger.error(f"An unexpected error occurred while finding stunnel plugins: {e}", exc_info=True)
            return None, None

    def _configure_existing_tunnel(self, stunnel_id: str, src_region: str, src_agent: str, src_port: str,
                                   dst_region: str, dst_agent: str, dst_host: str, dst_port: str,
                                   buffer_size: str, src_plugin_id: str, dst_plugin_id: str) -> dict:
        """
        Configure a tunnel using existing plugins.

        Args:
            stunnel_id: A unique ID for the tunnel.
            src_region: The source region.
            src_agent: The source agent.
            src_port: The source port.
            dst_region: The destination region.
            dst_agent: The destination agent.
            dst_host: The destination host.
            dst_port: The destination port.
            buffer_size: The buffer size for the tunnel.
            src_plugin_id: The ID of the source stunnel plugin.
            dst_plugin_id: The ID of the destination stunnel plugin.
        """
        try:
            self.logger.info(f"Configuring existing tunnel {stunnel_id} from {src_region}/{src_agent} to {dst_region}/{dst_agent}")

            message_event_type = 'CONFIG'
            message_payload = {
                'action': 'configsrctunnel',
                'action_src_port': src_port,
                'action_dst_host': dst_host,
                'action_dst_port': dst_port,
                'action_dst_region': dst_region,
                'action_dst_agent': dst_agent,
                'action_dst_plugin': dst_plugin_id,
                'action_buffer_size': buffer_size,
                'action_stunnel_id': stunnel_id,
            }

            result = self.client.messaging.global_plugin_msgevent(True, message_event_type, message_payload, src_region, src_agent, src_plugin_id)
            self.logger.info(f"Tunnel configuration result: {result}")
            if 'stunnel_config' in result:
                return json.loads(decompress_param(result['stunnel_config']))


        except Exception as e:
            self.logger.error(f"Error configuring existing tunnel: {e}")
            return {}

    def find_existing_stunnel_plugin(self, region: str, agent: str) -> Optional[str]:
        """
        Find an existing stunnel system plugin on a single agent.

        Args:
            region: The agent's region.
            agent: The agent's name.

        Returns:
            The plugin_id of the stunnel plugin, or None if not found.
        """
        try:
            # Directly query the agent for its plugins
            self.logger.info(f"Querying plugins for agent: {region}/{agent}")
            all_plugins = self.client.agents.list_plugin_agent(region, agent)

            # Search for the specific stunnel plugin
            for plugin in all_plugins:
                current_plugin_id = plugin.get("plugin_id", "")
                if plugin.get("pluginname") == "io.cresco.stunnel" and \
                        (current_plugin_id.startswith("system-") or current_plugin_id.startswith("systems-")):
                    self.logger.info(f"Found stunnel plugin '{current_plugin_id}' on agent {region}/{agent}.")
                    return current_plugin_id  # Return the found plugin ID immediately

            # If the loop completes without finding the plugin
            return None

        except Exception as e:
            # Log the error with traceback information for better debugging
            self.logger.error(f"Error finding stunnel plugin on {region}/{agent}: {e}", exc_info=True)
            # Return a default value consistent with the function's return type
            return None

    def get_tunnel_list(self, src_region: str, src_agent: str, src_plugin_id: str) -> dict | None:
        """
        Configure a tunnel using existing plugins.

        Args:
            src_region: The source region.
            src_agent: The source agent.
            src_plugin_id: The ID of the source stunnel plugin.
        """
        try:

            message_event_type = 'EXEC'
            message_payload = {
                'action': 'listtunnels',
            }

            result = self.client.messaging.global_plugin_msgevent(True, message_event_type, message_payload, src_region, src_agent, src_plugin_id)
            if 'tunnels' in result:
                return json.loads(result['tunnels'])


        except Exception as e:
            self.logger.error(f"Error configuring existing tunnel: {e}")
            return {}

    def get_tunnel_status(self, src_region: str, src_agent: str, src_plugin_id: str, stunnel_id: str) -> dict | None:
        """
        Configure a tunnel using existing plugins.

        Args:
            src_region: The source region.
            src_agent: The source agent.
            src_plugin_id: The ID of the source stunnel plugin.
            action_stunnel_id: The ID of the action stunnel.
        """
        try:

            message_event_type = 'EXEC'
            message_payload = {
                'action': 'gettunnelstatus',
                'action_stunnel_id': stunnel_id
            }

            result = self.client.messaging.global_plugin_msgevent(True, message_event_type, message_payload, src_region, src_agent, src_plugin_id)
            if 'tunnel_status' in result:
                return result['tunnel_status']


        except Exception as e:
            self.logger.error(f"Error configuring existing tunnel: {e}")
            return {}


    def get_tunnel_config(self, src_region: str, src_agent: str, src_plugin_id: str, stunnel_id: str) -> dict | None:
        """
        Configure a tunnel using existing plugins.

        Args:
            src_region: The source region.
            src_agent: The source agent.
            src_plugin_id: The ID of the source stunnel plugin.
            action_stunnel_id: The ID of the action stunnel.
        """
        try:

            message_event_type = 'EXEC'
            message_payload = {
                'action': 'gettunnelconfig',
                'action_stunnel_id': stunnel_id
            }

            result = self.client.messaging.global_plugin_msgevent(True, message_event_type, message_payload, src_region, src_agent, src_plugin_id)
            if 'tunnel_config' in result:
                return json.loads(result['tunnel_config'])


        except Exception as e:
            self.logger.error(f"Error configuring existing tunnel: {e}")
            return {}


