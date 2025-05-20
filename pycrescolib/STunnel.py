import json
import os
import time
import logging
import urllib
from typing import Dict, Any, Optional, Callable
from urllib import request
import yaml


class STunnel:
    """
    STunnel class for creating and managing secure tunnels between Cresco nodes.
    
    This class provides a simplified interface for creating secure tunnels between 
    different nodes in a Cresco environment, handling the deployment of required plugins,
    configuration, and monitoring.
    """
    
    def __init__(self, client, logger=None):
        """
        Initialize the STunnel class with a Cresco client
        
        Args:
            client: A connected pycrescolib clientlib instance
            logger: Optional logger instance (will create one if not provided)
        """
        # Store the client reference
        self.client = client
        self.dp = None
        self.pipeline_id = None
        
        # Setup logging if not provided
        if logger:
            self.logger = logger
        else:
            logging.basicConfig(level=logging.INFO)
            self.logger = logging.getLogger(__name__)
            
        # Create plugins directory if it doesn't exist
        os.makedirs("plugins", exist_ok=True)
            
    def create(self, 
               stunnel_id: str, 
               src_region: str, 
               src_agent: str, 
               src_port: int,
               dst_region: str, 
               dst_agent: str, 
               dst_host: str, 
               dst_port: int,
               buffer_size: int = 1024,
               watchdog_timeout: int = 30) -> Dict[str, Any]:
        """
        Create a secure tunnel between source and destination nodes.
        
        Args:
            stunnel_id: Unique identifier for this tunnel
            src_region: Source region (where the tunnel starts)
            src_agent: Source agent (where the tunnel starts)
            src_port: Source port to tunnel from
            dst_region: Destination region (where the tunnel ends)
            dst_agent: Destination agent (where the tunnel ends)
            dst_host: Destination host to connect to
            dst_port: Destination port to connect to
            buffer_size: Buffer size for data transfer (default: 1024)
            watchdog_timeout: Watchdog timeout in seconds (default: 30)
            
        Returns:
            Dictionary containing tunnel information including pipeline_id
        """
        self.logger.info(f"Creating secure tunnel {stunnel_id} from {src_region}/{src_agent}:{src_port} "
                         f"to {dst_region}/{dst_agent}:{dst_host}:{dst_port}")
        
        try:
            # Download and upload plugin
            jar_file_path = self._get_plugin_from_git(
                "https://github.com/CrescoEdge/stunnel/releases/download/1.2-SNAPSHOT/stunnel-1.2-SNAPSHOT.jar")
            reply = self._upload_plugin(jar_file_path)
            
            # Get plugin configuration
            from pycrescolib.utils import decompress_param
            config_str = decompress_param(reply['configparams'])
            configparams = json.loads(config_str)
            
            # Create pipeline configuration
            cadl = self._create_pipeline_config(
                stunnel_id, 
                configparams,
                src_region, 
                src_agent, 
                dst_region, 
                dst_agent
            )
            
            # Submit pipeline
            reply = self.client.globalcontroller.submit_pipeline(cadl)
            self.pipeline_id = reply['gpipeline_id']
            
            # Get pipeline info for plugin IDs
            pipeline_config = self.client.globalcontroller.get_pipeline_info(self.pipeline_id)
            
            # Wait for pipeline to come online
            if not self._wait_for_pipeline(self.pipeline_id):
                raise Exception(f"Timeout waiting for pipeline {self.pipeline_id} to come online")
                
            # Configure the source tunnel with destination information
            self._configure_source_tunnel(
                pipeline_config,
                src_region,
                src_agent,
                src_port,
                dst_region,
                dst_agent,
                dst_host,
                dst_port,
                buffer_size,
                watchdog_timeout,
                stunnel_id
            )
            
            # Return tunnel information
            return {
                'status': 'success',
                'stunnel_id': stunnel_id,
                'pipeline_id': self.pipeline_id,
                'src': {
                    'region': src_region,
                    'agent': src_agent,
                    'port': src_port
                },
                'dst': {
                    'region': dst_region,
                    'agent': dst_agent,
                    'host': dst_host,
                    'port': dst_port
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error creating secure tunnel: {e}", exc_info=True)
            return {
                'status': 'error',
                'message': str(e)
            }
        
    def create_from_yaml(self, yaml_path: str):
        """
        Create multiple stunnels from a YAML configuration file.
        
        Args:
            yaml_path: Path to the YAML file containing stunnel configurations.
        """
        if not os.path.exists(yaml_path):
            self.logger.error(f"YAML config file not found: {yaml_path}")
            return

        try:
            with open(yaml_path, 'r') as f:
                config = yaml.safe_load(f)
        except Exception as e:
            self.logger.error(f"Failed to load YAML file: {e}")
            return

        if config.get("version") != 2 or "stunnels" not in config:
            self.logger.error("Invalid YAML format or missing 'stunnels' section.")
            return

        results = []

        for stunnel in config["stunnels"]:
            try:
                result = self.create(
                    stunnel_id=stunnel["stunnel_id"],
                    src_region=stunnel["src_region"],
                    src_agent=stunnel["src_agent"],
                    src_port=stunnel["src_port"],
                    dst_region=stunnel["dst_region"],
                    dst_agent=stunnel["dst_agent"],
                    dst_host=stunnel["dst_host"],
                    dst_port=stunnel["dst_port"],
                    buffer_size=stunnel.get("buffer_size", 1024)
                )
                self.logger.info(f"Created stunnel {stunnel.get('name', stunnel['stunnel_id'])}: {result}")
                results.append(result)
            except Exception as e:
                self.logger.error(f"Failed to create stunnel {stunnel.get('name', '')}: {e}")

        return results
        
    def destroy(self, pipeline_id: Optional[str] = None) -> bool:
        """
        Destroy a secure tunnel by removing its pipeline.
        
        Args:
            pipeline_id: Pipeline ID to destroy (uses stored ID if None)
            
        Returns:
            True if successful, False otherwise
        """
        if pipeline_id is None:
            pipeline_id = self.pipeline_id
            
        if not pipeline_id:
            self.logger.error("No pipeline ID provided or stored")
            return False
            
        try:
            self.logger.info(f"Destroying secure tunnel pipeline {pipeline_id}")
            result = self.client.globalcontroller.remove_pipeline(pipeline_id)
            
            if result:
                self.logger.info(f"Successfully destroyed pipeline {pipeline_id}")
                if pipeline_id == self.pipeline_id:
                    self.pipeline_id = None
                return True
            else:
                self.logger.error(f"Failed to destroy pipeline {pipeline_id}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error destroying secure tunnel: {e}", exc_info=True)
            return False
    
    def status(self, pipeline_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get the status of a secure tunnel.
        
        Args:
            pipeline_id: Pipeline ID to check (uses stored ID if None)
            
        Returns:
            Dictionary containing status information
        """
        if pipeline_id is None:
            pipeline_id = self.pipeline_id
            
        if not pipeline_id:
            return {'status': 'error', 'message': 'No pipeline ID provided or stored'}
            
        try:
            status_code = self.client.globalcontroller.get_pipeline_status(pipeline_id)
            pipeline_info = self.client.globalcontroller.get_pipeline_info(pipeline_id)
            
            status_map = {
                0: 'unknown',
                1: 'initializing',
                5: 'configuring',
                10: 'active',
                15: 'failed',
                20: 'shutting_down',
                30: 'complete'
            }
            
            return {
                'pipeline_id': pipeline_id,
                'status_code': status_code,
                'status': status_map.get(status_code, 'unknown'),
                'info': pipeline_info
            }
            
        except Exception as e:
            self.logger.error(f"Error getting secure tunnel status: {e}", exc_info=True)
            return {'status': 'error', 'message': str(e)}
    
    def list_tunnels(self) -> Dict[str, Any]:
        """
        List all active secure tunnels.
        
        Returns:
            Dictionary containing tunnel information
        """
        try:
            pipelines = self.client.globalcontroller.get_pipeline_list()
            stunnel_pipelines = []
            
            for pipeline in pipelines:
                try:
                    pipeline_info = self.client.globalcontroller.get_pipeline_info(pipeline)
                    # Check if this is a stunnel pipeline by looking at node names
                    if any('SRC Plugin' in str(node.get('node_name', '')) for node in pipeline_info.get('nodes', [])):
                        status_code = self.client.globalcontroller.get_pipeline_status(pipeline)
                        stunnel_pipelines.append({
                            'pipeline_id': pipeline,
                            'status_code': status_code,
                            'info': pipeline_info
                        })
                except Exception:
                    # Skip pipelines that can't be accessed
                    pass
                    
            return {
                'status': 'success',
                'count': len(stunnel_pipelines),
                'tunnels': stunnel_pipelines
            }
            
        except Exception as e:
            self.logger.error(f"Error listing secure tunnels: {e}", exc_info=True)
            return {'status': 'error', 'message': str(e)}
    
    def _create_pipeline_config(self, stunnel_id, configparams, src_region, src_agent, dst_region, dst_agent):
        """Create pipeline configuration for stunnel deployment"""
        cadl = {
            'pipeline_id': '0',
            'pipeline_name': stunnel_id,
            'nodes': [],
            'edges': []
        }

        # Source node
        params0 = {
            'pluginname': configparams['pluginname'],
            'md5': configparams['md5'],
            'version': configparams['version'],
            'location_region': src_region,
            'location_agent': src_agent,
        }

        node0 = {
            'type': 'dummy',
            'node_name': 'SRC Plugin',
            'node_id': 0,
            'isSource': False,
            'workloadUtil': 0,
            'params': params0
        }

        # Destination node
        params1 = {
            'pluginname': configparams['pluginname'],
            'md5': configparams['md5'],
            'version': configparams['version'],
            'location_region': dst_region,
            'location_agent': dst_agent,
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
        
        return cadl
    
    def _configure_source_tunnel(self, pipeline_config, src_region, src_agent, src_port, 
                               dst_region, dst_agent, dst_host, dst_port, 
                               buffer_size, watchdog_timeout, stunnel_id):
        """Configure source tunnel with destination information"""
        try:
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
                'action_watchdog_timeout': watchdog_timeout,
                'action_stunnel_id': stunnel_id,
            }

            result = self.client.messaging.global_plugin_msgevent(
                True, message_event_type, message_payload, 
                src_region, src_agent, src_plugin
            )
            
            self.logger.info(f"Source tunnel configuration result: {result}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error configuring source tunnel: {e}", exc_info=True)
            raise
    
    def _get_plugin_from_git(self, src_url: str, force: bool = False) -> str:
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

    def _upload_plugin(self, jar_path: str) -> Dict[str, Any]:
        """Upload a plugin to the global controller.

        Args:
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

    def _wait_for_pipeline(self, pipeline_id: str, target_status: int = 10, timeout: int = 60) -> bool:
        """Wait for pipeline to reach desired status.

        Args:
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