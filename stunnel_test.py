import json
import os
import time
import logging
import urllib
import uuid
from typing import Dict, Any, Tuple, List
from urllib import request

from pycrescolib.utils import decompress_param, compress_param, json_serialize


class STunnelTest:
    def __init__(self, client, logger=None):
        """
        Initialize the STunnelTest class with a Cresco client

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

    def create_tunnel(self, stunnel_id: str, src_region: str, src_agent: str, src_port: str,
                      dst_region: str, dst_agent: str, dst_host: str, dst_port: str,
                      buffer_size: str, use_existing_plugins: bool = False) -> None:
        """
        Create a tunnel, either by deploying new plugins or using existing ones.

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
            use_existing_plugins: If True, try to use existing system plugins.
        """
        if use_existing_plugins:
            self.logger.info("Attempting to create tunnel using existing system plugins.")
            src_plugin_id, dst_plugin_id, all_src_plugins, all_dst_plugins = self._find_existing_stunnel_plugins(src_region, src_agent, dst_region, dst_agent)

            if src_plugin_id and dst_plugin_id:
                self.logger.info(f"Found existing stunnel plugins: src_plugin_id={src_plugin_id}, dst_plugin_id={dst_plugin_id}")
                self._configure_existing_tunnel(stunnel_id, src_region, src_agent, src_port,
                                                dst_region, dst_agent, dst_host, dst_port,
                                                buffer_size, src_plugin_id, dst_plugin_id)
                return
            else:
                self.logger.error("PROCESS FAILED: Could not find the required existing system stunnel plugins.")
                self.logger.error("Please ensure that stunnel plugins are running on both the source and destination agents and that their names start with 'system-' or 'systems-'.")
                self.logger.info(f"Plugins found on source agent ({src_region}/{src_agent}): {json.dumps(all_src_plugins, indent=2)}")
                self.logger.info(f"Plugins found on destination agent ({dst_region}/{dst_agent}): {json.dumps(all_dst_plugins, indent=2)}")
                return # Stop the process

        else:
            self.logger.info("Creating tunnel using CADL deployment.")
            self._create_tunnel_with_cadl(stunnel_id, src_region, src_agent, src_port,
                                         dst_region, dst_agent, dst_host, dst_port,
                                         buffer_size)

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


    def _create_tunnel_with_cadl(self, stunnel_id, src_region, src_agent, src_port, dst_region, dst_agent, dst_host, dst_port, buffer_size) -> None:
        """Deploy a file repository system across multiple nodes.

        Args:
            client: The Cresco client
            dst_region: Target region (controller)
            dst_agent: Target agent (controller)
        """
        self.logger.info(f"Starting multi-node stunnel deployment with controller at {dst_region}/{dst_agent}")

        try:

            # (1) Make sure the stunnel plugin exists on the GC

            # Download and upload plugin
            #jar_file_path = self.get_plugin_from_git(
            #    "https://github.com/CrescoEdge/stunnel/releases/download/1.2-SNAPSHOT/stunnel-1.2-SNAPSHOT.jar")
            jar_file_path = '/Users/cody/IdeaProjects/stunnel/target/stunnel-1.2-SNAPSHOT.jar'
            reply = self.upload_plugin(jar_file_path)

            # Get plugin configuration
            config_str = decompress_param(reply['configparams'])
            self.logger.info(f"Plugin config: {config_str}")

            # (2) Deploy the plugins to the agent(s) where you want to enable tunnels
            # * Note this just pushes the plugins to the agent(s) it does not establish stunnel configurations

            # Create pipeline configuration
            configparams = json.loads(config_str)

            cadl = {
                'pipeline_id': '0',
                'pipeline_name': stunnel_id,
                'nodes': [],
                'edges': []
            }

            # Source node (MS4500)
            params0 = {
                'pluginname': configparams['pluginname'],
                'md5': configparams['md5'],
                'version': configparams['version'],
                'location_region': src_region,
                'location_agent': src_agent,
                #'src_port': src_port,
                #'stunnel_id': stunnel_id,
                #'buffer_size': buffer_size,
            }

            node0 = {
                'type': 'dummy',
                'node_name': 'SRC Plugin',
                'node_id': 0,
                'isSource': False,
                'workloadUtil': 0,
                'params': params0
            }

            # Destination node (controller)
            params1 = {
                'pluginname': configparams['pluginname'],
                'md5': configparams['md5'],
                'version': configparams['version'],
                'location_region': dst_region,
                'location_agent': dst_agent,
                #'dst_host': dst_host,
                #'dst_port': dst_port,
            }

            node1 = {
                'type': 'dummy',
                'node_name': 'DST Plugin',
                'node_id': 1,
                'isSource': False,
                'workloadUtil': 0,
                'params': params1
            }

            # Edge
            edge0 = {
                'edge_id': 0,
                'node_from': 0,
                'node_to': 1,
                'params': {}
            }

            cadl['nodes'].append(node0)
            cadl['nodes'].append(node1)
            cadl['edges'].append(edge0)

            # Submit pipeline
            reply = self.client.globalcontroller.submit_pipeline(cadl)
            pipeline_id = reply['gpipeline_id']

            # this is needed for the config
            pipeline_config = self.client.globalcontroller.get_pipeline_info(pipeline_id)

            self.logger.info(f"Pipeline Config: {pipeline_config}")

            # Wait for pipeline to come online
            is_online = self.wait_for_pipeline(pipeline_id)
            if is_online:
                # Note: Pipeline is not removed in this pycrescolib_test to allow ongoing sync
                self.logger.info("Multi-node file repository pycrescolib_test completed successfully")
            else:
                self.logger.info("Multi-node file repository pycrescolib_test failed")

            # (3) If plugins are in place lets configure them
            # pipeline_config is used to determine the plugin ids used in the initial plugin pair push


            dst_plugin = pipeline_config['nodes'][1]['node_id']
            src_plugin = pipeline_config['nodes'][0]['node_id']

            message_event_type = 'CONFIG'
            message_payload = {
                'action': 'configsrctunnel',
                'action_src_port': src_port,
                'action_dst_host': dst_host,
                'action_dst_port': dst_port,
                'action_dst_region': dst_region,
                'action_dst_agent': dst_agent,
                'action_dst_plugin': dst_plugin,
                'action_buffer_size': buffer_size,
                'action_stunnel_id': stunnel_id,
            }

            #logger.info(f"Uploading plugin {configparams.get('pluginname')} to global repository")
            result = self.client.messaging.global_plugin_msgevent(True, message_event_type, message_payload, src_region, src_agent, src_plugin)
            print(result)

        except Exception as e:
            self.logger.error(f"Error in filerepo_deploy_multi_node: {e}", exc_info=True)

    def get_plugin_from_git(self, src_url: str, force: bool = False) -> str:
        """Download plugin JAR file from GitHub.

        Args:
            src_url: URL to the plugin JAR
            force: Whether to force download even if file exists

        Returns:
            Local path to downloaded JAR file
        """
        dst_file = src_url.rsplit('/', 1)[1]
        dst_path = os.path.join("plugins", dst_file)

        if force or not os.path.exists(dst_path):
            self.logger.info(f"Downloading {dst_file} plugin from {src_url}")
            try:
                request.urlretrieve(src_url, dst_path)
                self.logger.info(f"Downloaded {dst_file} successfully")
            except Exception as e:
                self.logger.error(f"Failed to download {dst_file}: {e}")
                raise
        else:
            self.logger.info(f"Using existing plugin file: {dst_path}")

        return dst_path

    def upload_plugin(self, jar_path: str) -> Dict[str, Any]:
        """Upload a plugin to the global controller.

        Args:
            client: The Cresco client
            jar_path: Path to the JAR file

        Returns:
            Response from upload operation
        """
        self.logger.info(f"Uploading plugin {jar_path} to global controller")
        try:
            reply = self.client.globalcontroller.upload_plugin_global(jar_path)
            self.logger.info(f"Upload status: {reply.get('status_code', 'unknown')}")
            return reply
        except Exception as e:
            self.logger.error(f"Error uploading plugin: {e}")
            raise

    def wait_for_pipeline(self, pipeline_id: str, target_status: int = 10, timeout: int = 60) -> bool:
        """Wait for pipeline to reach desired status.

        Args:
            client: The Cresco client
            pipeline_id: Pipeline ID to monitor
            target_status: Desired status code (default: 10 for online)
            timeout: Maximum wait time in seconds

        Returns:
            True if pipeline reached desired status, False otherwise
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                status = self.client.globalcontroller.get_pipeline_status(pipeline_id)
                if status == target_status:
                    self.logger.info(f"Pipeline {pipeline_id} reached status {target_status}")
                    return True

                self.logger.info(f"Waiting for pipeline {pipeline_id} to reach status {target_status}, current: {status}")
                time.sleep(2)
            except Exception as e:
                self.logger.error(f"Error checking pipeline status: {e}")
                time.sleep(2)

        self.logger.error(f"Timeout waiting for pipeline {pipeline_id} to reach status {target_status}")
        return False