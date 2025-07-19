import json
import logging
from typing import Dict, List, Tuple

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
                      buffer_size: str) -> None:
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
        src_plugin_id, dst_plugin_id, all_src_plugins, all_dst_plugins = self._find_existing_stunnel_plugins(src_region, src_agent, dst_region, dst_agent)

        if src_plugin_id and dst_plugin_id:
            self.logger.info(f"Found existing stunnel plugins: src_plugin_id={src_plugin_id}, dst_plugin_id={dst_plugin_id}")
            self._configure_existing_tunnel(stunnel_id, src_region, src_agent, src_port,
                                            dst_region, dst_agent, dst_host, dst_port,
                                            buffer_size, src_plugin_id, dst_plugin_id)
        else:
            self.logger.error("PROCESS FAILED: Could not find the required existing system stunnel plugins.")
            self.logger.error("Please ensure that stunnel plugins are running on both the source and destination agents and that their names start with 'system-' or 'systems-'.")
            self.logger.info(f"Plugins found on source agent ({src_region}/{src_agent}): {json.dumps(all_src_plugins, indent=2)}")
            self.logger.info(f"Plugins found on destination agent ({dst_region}/{dst_agent}): {json.dumps(all_dst_plugins, indent=2)}")

    def _find_existing_stunnel_plugins(self, src_region: str, src_agent: str, dst_region: str, dst_agent: str) -> Tuple[str, str, List[Dict], List[Dict]]:
        """
        Find existing stunnel system plugins on the source and destination agents.

        Args:
            src_region: The source region.
            src_agent: The source agent.
            dst_region: The destination region.
            dst_agent: The destination agent.

        Returns:
            A tuple containing (src_plugin_id, dst_plugin_id, all_src_plugins, all_dst_plugins).
        """
        try:
            src_plugin_id = None
            dst_plugin_id = None

            # Directly query the source agent for its plugins
            self.logger.info(f"Querying plugins for source agent: {src_region}/{src_agent}")
            all_src_plugins = self.client.agents.list_plugin_agent(src_region, src_agent)
            for plugin in all_src_plugins:
                plugin_id = plugin.get("plugin_id", "")
                if plugin.get("pluginname") == "io.cresco.stunnel" and (plugin_id.startswith("system-") or plugin_id.startswith("systems-")):
                    src_plugin_id = plugin_id
                    break

            # Directly query the destination agent for its plugins
            self.logger.info(f"Querying plugins for destination agent: {dst_region}/{dst_agent}")
            all_dst_plugins = self.client.agents.list_plugin_agent(dst_region, dst_agent)
            for plugin in all_dst_plugins:
                plugin_id = plugin.get("plugin_id", "")
                if plugin.get("pluginname") == "io.cresco.stunnel" and (plugin_id.startswith("system-") or plugin_id.startswith("systems-")):
                    dst_plugin_id = plugin_id
                    break

            return src_plugin_id, dst_plugin_id, all_src_plugins, all_dst_plugins
        except Exception as e:
            self.logger.error(f"Error finding existing stunnel plugins: {e}", exc_info=True)
            return None, None, [], []

    def _configure_existing_tunnel(self, stunnel_id: str, src_region: str, src_agent: str, src_port: str,
                                   dst_region: str, dst_agent: str, dst_host: str, dst_port: str,
                                   buffer_size: str, src_plugin_id: str, dst_plugin_id: str) -> None:
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

        except Exception as e:
            self.logger.error(f"Error configuring existing tunnel: {e}")