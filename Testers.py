"""
Cresco Framework Test Suite.

This module provides testing functions for various Cresco framework components including:
- File repository services
- Executor services
- AI API services
- Controller management
- Agent debugging
"""
import json
import random
import time
import uuid
import os
import logging
import urllib.request
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Callable

from pycrescolib.utils import compress_param, decompress_param, get_jar_info

# Configure module logger
logger = logging.getLogger(__name__)

# Directory for storing pycrescolib_test data
TEST_DATA_DIR = "test_data"
PLUGINS_DIR = "plugins"

# Ensure directories exist
os.makedirs(TEST_DATA_DIR, exist_ok=True)
os.makedirs(PLUGINS_DIR, exist_ok=True)


def get_plugin_from_git(src_url: str, force: bool = False) -> str:
    """Download plugin JAR file from GitHub.

    Args:
        src_url: URL to the plugin JAR
        force: Whether to force download even if file exists

    Returns:
        Local path to downloaded JAR file
    """
    dst_file = src_url.rsplit('/', 1)[1]
    dst_path = os.path.join(PLUGINS_DIR, dst_file)

    if force or not os.path.exists(dst_path):
        logger.info(f"Downloading {dst_file} plugin from {src_url}")
        try:
            urllib.request.urlretrieve(src_url, dst_path)
            logger.info(f"Downloaded {dst_file} successfully")
        except Exception as e:
            logger.error(f"Failed to download {dst_file}: {e}")
            raise
    else:
        logger.info(f"Using existing plugin file: {dst_path}")

    return dst_path


def filerepo_deploy_multi_node_rec(client, dst_region: str, dst_agent: str) -> None:
    """Deploy a file repository system with recursive scanning.

    Args:
        client: The Cresco client
        dst_region: Target region
        dst_agent: Target agent
    """
    logger.info(f"Starting multi-node recursive file repository deployment on {dst_region}/{dst_agent}")

    # Ensure client is connected
    if not wait_for_connection(client):
        logger.error("Client connection failed, aborting pycrescolib_test")
        return

    # Check controller status
    if not check_controller_active(client, dst_region, dst_agent):
        logger.error("Controller not active, aborting pycrescolib_test")
        return

    try:
        # Download and upload plugin (or use local path)
        jar_file_path = '/Users/cody/IdeaProjects/filerepo/target/filerepo-1.1-SNAPSHOT.jar'
        reply = upload_plugin(client, jar_file_path)

        # Get plugin configuration
        config_str = decompress_param(reply['configparams'])
        logger.info(f"Plugin config: {config_str}")

        # Create unique repository name
        filerepo_name = str(uuid.uuid1())

        # Set up dataplane for monitoring (optional)
        stream_query = f"filerepo_name='{filerepo_name}' AND broadcast"
        logger.info(f"Client stream query: {stream_query}")

        # Create pipeline configuration
        configparams = json.loads(config_str)

        cadl = {
            'pipeline_id': '0',
            'pipeline_name': str(uuid.uuid1()),
            'nodes': [],
            'edges': []
        }

        # Source node configuration
        params0 = {
            'pluginname': configparams['pluginname'],
            'md5': configparams['md5'],
            'version': configparams['version'],
            'persistence_code': '10',
            'location_region': 'global-region',
            'location_agent': 'myagent',
            'filerepo_name': filerepo_name,
            'scan_dir': '/Users/cody/Downloads/test_out',
            'scan_recursive': 'true'
        }

        node0 = {
            'type': 'dummy',
            'node_name': 'SRC Plugin',
            'node_id': 0,
            'isSource': False,
            'workloadUtil': 0,
            'params': params0
        }

        # Destination node configuration
        params1 = {
            'pluginname': configparams['pluginname'],
            'md5': configparams['md5'],
            'version': configparams['version'],
            'persistence_code': '10',
            'location_region': 'global-region',
            'location_agent': 'global-controller',
            'filerepo_name': filerepo_name,
            'repo_dir': '/Users/cody/Downloads/test_in'
        }

        node1 = {
            'type': 'dummy',
            'node_name': 'DST Plugin',
            'node_id': 1,
            'isSource': False,
            'workloadUtil': 0,
            'params': params1
        }

        # Edge configuration
        edge0 = {
            'edge_id': 0,
            'node_from': 0,
            'node_to': 1,
            'params': {}
        }

        # Add nodes and edges to pipeline
        cadl['nodes'].append(node0)
        cadl['nodes'].append(node1)
        cadl['edges'].append(edge0)

        # Submit pipeline
        reply = client.globalcontroller.submit_pipeline(cadl)
        logger.info(f"Status of recursive filerepo pipeline submit: {reply}")

        pipeline_id = reply['gpipeline_id']

        # Wait for pipeline to come online
        wait_for_pipeline(client, pipeline_id)

        # Note: This pycrescolib_test keeps the pipeline running for ongoing sync
        logger.info("Multi-node recursive file repository pycrescolib_test started successfully")

    except Exception as e:
        logger.error(f"Error in filerepo_deploy_multi_node_rec: {e}", exc_info=True)


def filerepo_deploy_multi_node_tox_results(client, dst_region: str, dst_agent: str) -> None:
    """Deploy a file repository system for toxicology results data.

    Args:
        client: The Cresco client
        dst_region: Target region (controller)
        dst_agent: Target agent (controller)
    """
    logger.info(f"Starting toxicology results file repository deployment with controller at {dst_region}/{dst_agent}")

    # Ensure client is connected
    if not wait_for_connection(client):
        logger.error("Client connection failed, aborting pycrescolib_test")
        return

    # Check controller status
    if not check_controller_active(client, dst_region, dst_agent):
        logger.error("Controller not active, aborting pycrescolib_test")
        return

    try:
        # Setup logging
        log = setup_logging_stream(client, dst_region, dst_agent)

        # Download and upload plugin
        jar_file_path = get_plugin_from_git(
            "https://github.com/CrescoEdge/filerepo/releases/download/1.1-SNAPSHOT/filerepo-1.1-SNAPSHOT.jar")
        reply = upload_plugin(client, jar_file_path)

        # Get plugin configuration
        config_str = decompress_param(reply['configparams'])

        # Create unique repository name
        filerepo_name = str(uuid.uuid1())

        # Set up dataplane for monitoring (optional)
        stream_query = f"filerepo_name='{filerepo_name}' AND broadcast"
        logger.info(f"Client stream query: {stream_query}")

        # Create pipeline configuration
        configparams = json.loads(config_str)

        cadl = {
            'pipeline_id': '0',
            'pipeline_name': str(uuid.uuid1()),
            'nodes': [],
            'edges': []
        }

        # Source node (MS4500)
        params0 = {
            'pluginname': configparams['pluginname'],
            'md5': configparams['md5'],
            'version': configparams['version'],
            'persistence_code': '10',
            'location_region': 'lab',
            'location_agent': 'MS4500',
            'filerepo_name': filerepo_name,
            'scan_dir': 'f:\\2022\\PMDRUG',
            'scan_recursive': 'true'
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
            'persistence_code': '10',
            'location_region': 'lab',
            'location_agent': 'controller',
            'filerepo_name': filerepo_name,
            'repo_dir': '\\\\ukhcdata\\dept\\Laboratory Services\\Chandler Clinical Lab\\HLB CoreLabMT\\SPECIAL CHEMISTRY\\RawData\\MS4500\\RESULTS'
        }

        node1 = {
            'type': 'dummy',
            'node_name': 'DST Plugin',
            'node_id': 1,
            'isSource': False,
            'workloadUtil': 0,
            'params': params1
        }

        # Edge configuration
        edge0 = {
            'edge_id': 0,
            'node_from': 0,
            'node_to': 1,
            'params': {}
        }

        # Add nodes and edges to pipeline
        cadl['nodes'].append(node0)
        cadl['nodes'].append(node1)
        cadl['edges'].append(edge0)

        # Submit pipeline
        reply = client.globalcontroller.submit_pipeline(cadl)
        logger.info(f"Status of toxicology results filerepo pipeline submit: {reply}")

        pipeline_id = reply['gpipeline_id']

        # Wait for pipeline to come online
        wait_for_pipeline(client, pipeline_id)

        # Allow time for synchronization (ongoing)
        logger.info("Waiting for file synchronization (2 minutes)...")
        time.sleep(120)

        # Note: Pipeline is not removed in this pycrescolib_test to allow ongoing sync
        logger.info("Toxicology results file repository pycrescolib_test completed successfully")

    except Exception as e:
        logger.error(f"Error in filerepo_deploy_multi_node_tox_results: {e}", exc_info=True)


def pathworker_executor_deploy_single_node_plugin(client, dst_region: str, dst_agent: str) -> None:
    """Deploy a pathworker executor plugin for digital path processing.

    Args:
        client: The Cresco client
        dst_region: Target region
        dst_agent: Target agent
    """
    logger.info(f"Starting pathworker executor deployment on {dst_region}/{dst_agent}")

    # Ensure client is connected
    if not wait_for_connection(client):
        logger.error("Client connection failed, aborting pycrescolib_test")
        return

    # Check controller status
    if not check_controller_active(client, dst_region, dst_agent):
        logger.error("Controller not active, aborting pycrescolib_test")
        return

    try:
        # Create stream name for dataplane
        stream_name = str(uuid.uuid1())

        # Set up dataplane
        stream_query = f"stream_name='{stream_name}'"
        logger.info(f"Client stream query: {stream_query}")

        # Custom callback to parse JSON responses when possible
        def dp_callback(message):
            try:
                payload = json.loads(str(message))
                logger.info(f"JSON payload: {payload}")
            except json.JSONDecodeError:
                logger.info(f"Raw message: {message}")

        dp = setup_dataplane_stream(client, stream_query, dp_callback)

        # Set up executor configuration (using predefined parameters)
        configparams = {
            'pluginname': 'io.cresco.executor',
            'version': '1.1.0.SNAPSHOT-2021-12-02T195342Z',
            'md5': '893deca0083ce5e301071577dccfdc9c'
        }

        # Add plugin to agent
        logger.info(f"Adding pathworker executor plugin to {dst_region}/{dst_agent}")
        reply = client.agents.add_plugin_agent(dst_region, dst_agent, configparams, None)
        logger.info(f"Pathworker executor plugin added: {reply}")
        executor_plugin_id = reply['pluginid']

        # Wait for plugin to start
        while client.agents.status_plugin_agent(dst_region, dst_agent, executor_plugin_id)['status_code'] != '10':
            logger.info("Waiting for pathworker executor plugin to start...")
            time.sleep(1)

        # Send config message to executor plugin
        message_event_type = 'CONFIG'
        message_payload = {
            'action': 'config_process',
            'stream_name': stream_name,
            'command': 'cd /digitalpathprocessor/webapiclient; python3 client.py --test_mode=0'
        }

        result = client.messaging.global_plugin_msgevent(
            True, message_event_type, message_payload, dst_region, dst_agent, executor_plugin_id)
        logger.info(f"Config result: {result}")
        logger.info(f"Config status: {result.get('config_status', 'unknown')}")

        # Start process
        message_payload['action'] = 'start_process'
        result = client.messaging.global_plugin_msgevent(
            True, message_event_type, message_payload, dst_region, dst_agent, executor_plugin_id)
        logger.info(f"Start status: {result.get('start_status', 'unknown')}")

        # Check status
        message_payload['action'] = 'status_process'
        result = client.messaging.global_plugin_msgevent(
            True, message_event_type, message_payload, dst_region, dst_agent, executor_plugin_id)
        logger.info(f"Initial status: {result}")

        # Wait for processing
        time.sleep(5)

        # Check status again
        result = client.messaging.global_plugin_msgevent(
            True, message_event_type, message_payload, dst_region, dst_agent, executor_plugin_id)
        logger.info(f"Status after 5 seconds: {result}")

        # Wait for more processing
        time.sleep(30)

        # End process
        message_payload['action'] = 'end_process'
        result = client.messaging.global_plugin_msgevent(
            True, message_event_type, message_payload, dst_region, dst_agent, executor_plugin_id)
        logger.info(f"End result: {result}")
        logger.info(f"End status: {result.get('end_status', 'unknown')}")

        # Remove plugin
        logger.info(f"Removing plugin {executor_plugin_id}")
        client.agents.remove_plugin_agent(dst_region, dst_agent, executor_plugin_id)

        # Wait for plugin to shut down
        while client.agents.status_plugin_agent(dst_region, dst_agent, executor_plugin_id)['status_code'] == '10':
            logger.info("Waiting for plugin to shut down...")
            time.sleep(1)

        logger.info("Pathworker executor pycrescolib_test completed successfully")

    except Exception as e:
        logger.error(f"Error in pathworker_executor_deploy_single_node_plugin: {e}", exc_info=True)


def interactive_executor_deploy_single_node_plugin_pushonly(client, dst_region: str, dst_agent: str) -> None:
    """Deploy an interactive executor service with push-only mode.

    Args:
        client: The Cresco client
        dst_region: Target region
        dst_agent: Target agent
    """
    logger.info(f"Starting push-only interactive executor deployment on {dst_region}/{dst_agent}")

    # Ensure client is connected
    if not wait_for_connection(client):
        logger.error("Client connection failed, aborting pycrescolib_test")
        return

    # Check controller status
    if not check_controller_active(client, dst_region, dst_agent):
        logger.error("Controller not active, aborting pycrescolib_test")
        return

    try:
        # Create a unique identifier for the stream
        ident_id = str(uuid.uuid1())

        # Upload plugin (using local path)
        jar_file_path = '/Users/cody/IdeaProjects/executor/target/executor-1.1-SNAPSHOT.jar'
        reply = upload_plugin(client, jar_file_path)

        # Extract configuration parameters
        configparams = json.loads(decompress_param(reply['configparams']))
        logger.info(f"Plugin configuration loaded")

        # Add plugin to agent
        reply = client.agents.add_plugin_agent(dst_region, dst_agent, configparams, None)
        logger.info(f"Push-only interactive executor plugin added: {reply}")
        executor_plugin_id = reply['pluginid']

        # Wait for plugin to start
        while client.agents.status_plugin_agent(dst_region, dst_agent, executor_plugin_id)['status_code'] != '10':
            logger.info("Waiting for executor plugin to start...")
            time.sleep(1)

        # Send config message for interactive mode
        message_event_type = 'CONFIG'
        message_payload = {
            'action': 'config_process',
            'stream_name': ident_id,
            'command': '-interactive-'
        }

        result = client.messaging.global_plugin_msgevent(
            True, message_event_type, message_payload, dst_region, dst_agent, executor_plugin_id)
        logger.info(f"Config result: {result}")
        logger.info(f"Config status: {result.get('config_status', 'unknown')}")

        # Start process
        message_payload['action'] = 'start_process'
        result = client.messaging.global_plugin_msgevent(
            True, message_event_type, message_payload, dst_region, dst_agent, executor_plugin_id)
        logger.info(f"Start status: {result.get('start_status', 'unknown')}")

        # Check status
        message_payload['action'] = 'status_process'
        result = client.messaging.global_plugin_msgevent(
            True, message_event_type, message_payload, dst_region, dst_agent, executor_plugin_id)
        logger.info(f"Status result: {result}")

        # Note: In push-only mode, we don't create or connect to a dataplane
        # This mode is useful when the dataplane is connected elsewhere
        logger.info("Push-only mode activated - no dataplane connection")

        # For this example, we'll just wait for a bit
        logger.info("Waiting 5 seconds...")
        time.sleep(5)

        # In a real scenario, you would send commands through another channel
        # or leave the executor running for other processes to interact with

        logger.info("Push-only interactive executor pycrescolib_test completed")

        # Note: We're not calling end_process or removing the plugin in this example
        # This is intentional for the push-only mode, where the plugin might be
        # accessed by other processes

    except Exception as e:
        logger.error(f"Error in interactive_executor_deploy_single_node_plugin_pushonly: {e}", exc_info=True)

def wait_for_connection(client, max_attempts: int = 10) -> bool:
    """Wait for client to connect, with retry logic.

    Args:
        client: The Cresco client
        max_attempts: Maximum number of connection attempts

    Returns:
        True if connected, False otherwise
    """
    attempt = 0
    while not client.connected() and attempt < max_attempts:
        logger.info("Waiting on client connection...")
        time.sleep(min(10, 2 ** attempt))  # Exponential backoff
        client.connect()
        attempt += 1

    if client.connected():
        logger.info("Client connected successfully")
        return True
    else:
        logger.error(f"Failed to connect after {max_attempts} attempts")
        return False


def check_controller_active(client, dst_region: str, dst_agent: str) -> bool:
    """Check if controller is active and log status.

    Args:
        client: The Cresco client
        dst_region: Destination region
        dst_agent: Destination agent

    Returns:
        True if controller is active, False otherwise
    """
    try:
        status = client.agents.get_controller_status(dst_region, dst_agent)
        logger.info(f"Controller status for {dst_region}/{dst_agent}: {status}")

        active = client.agents.is_controller_active(dst_region, dst_agent)
        if active:
            logger.info(f"Controller {dst_region}/{dst_agent} is active")
        else:
            logger.warning(f"Controller {dst_region}/{dst_agent} is not active")

        return active
    except Exception as e:
        logger.error(f"Error checking controller status: {e}")
        return False


def wait_for_pipeline(client, pipeline_id: str, target_status: int = 10, timeout: int = 60) -> bool:
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
            status = client.globalcontroller.get_pipeline_status(pipeline_id)
            if status == target_status:
                logger.info(f"Pipeline {pipeline_id} reached status {target_status}")
                return True

            logger.info(f"Waiting for pipeline {pipeline_id} to reach status {target_status}, current: {status}")
            time.sleep(2)
        except Exception as e:
            logger.error(f"Error checking pipeline status: {e}")
            time.sleep(2)

    logger.error(f"Timeout waiting for pipeline {pipeline_id} to reach status {target_status}")
    return False


def setup_logging_stream(client, dst_region: str, dst_agent: str, callback: Optional[Callable] = None) -> Any:
    """Setup a log stream for the specified region/agent.

    Args:
        client: The Cresco client
        dst_region: Target region
        dst_agent: Target agent
        callback: Optional callback function for log messages

    Returns:
        Log streamer instance
    """
    if callback is None:
        def default_logger_callback(message):
            logger.info(f"Log message: {message}")

        callback = default_logger_callback

    logger.info(f"Setting up log stream for {dst_region}/{dst_agent}")
    log = client.get_logstreamer(callback)
    log.connect()
    log.update_config(dst_region, dst_agent)
    return log


def setup_dataplane_stream(client, stream_query: str, callback: Optional[Callable] = None) -> Any:
    """Setup a dataplane stream with the specified query.

    Args:
        client: The Cresco client
        stream_query: Stream query string
        callback: Optional callback function for data messages

    Returns:
        Dataplane instance
    """
    if callback is None:
        def default_dp_callback(message):
            try:
                data = json.loads(message)
                logger.info(f"Dataplane message: {data}")
            except json.JSONDecodeError:
                logger.info(f"Dataplane message (raw): {message}")

        callback = default_dp_callback

    logger.info(f"Setting up dataplane stream with query: {stream_query}")
    dp = client.get_dataplane(stream_query, callback)
    dp.connect()
    return dp


def upload_plugin(client, jar_path: str) -> Dict[str, Any]:
    """Upload a plugin to the global controller.

    Args:
        client: The Cresco client
        jar_path: Path to the JAR file

    Returns:
        Response from upload operation
    """
    logger.info(f"Uploading plugin {jar_path} to global controller")
    try:
        reply = client.globalcontroller.upload_plugin_global(jar_path)
        logger.info(f"Upload status: {reply.get('status_code', 'unknown')}")
        return reply
    except Exception as e:
        logger.error(f"Error uploading plugin: {e}")
        raise


# ===== FILE REPOSITORY TESTS =====

def filerepo_deploy_single_node(client, dst_region: str, dst_agent: str) -> None:
    """Deploy a file repository system on a single node.

    Args:
        client: The Cresco client
        dst_region: Target region
        dst_agent: Target agent
    """
    logger.info(f"Starting single-node file repository deployment on {dst_region}/{dst_agent}")

    # Ensure client is connected
    if not wait_for_connection(client):
        logger.error("Client connection failed, aborting pycrescolib_test")
        return

    # Check controller status
    if not check_controller_active(client, dst_region, dst_agent):
        logger.error("Controller not active, aborting pycrescolib_test")
        return

    try:
        # Setup logging
        log = setup_logging_stream(client, dst_region, dst_agent)

        # Download and upload plugin
        jar_file_path = get_plugin_from_git(
            "https://github.com/CrescoEdge/filerepo/releases/download/1.1-SNAPSHOT/filerepo-1.1-SNAPSHOT.jar")
        reply = upload_plugin(client, jar_file_path)

        # Get plugin configuration
        config_str = decompress_param(reply['configparams'])
        logger.info(f"Plugin config: {config_str}")

        # Create pycrescolib_test directories and data
        filerepo_name = str(uuid.uuid1())

        # Source directory setup
        src_repo_path = os.path.abspath(os.path.join(TEST_DATA_DIR, str(uuid.uuid1())))
        os.makedirs(src_repo_path, exist_ok=True)
        logger.info(f"Source repository path: {src_repo_path}")

        # Destination directory setup
        dst_repo_path = os.path.abspath(os.path.join(TEST_DATA_DIR, str(uuid.uuid1())))
        os.makedirs(dst_repo_path, exist_ok=True)
        logger.info(f"Destination repository path: {dst_repo_path}")

        # Create pycrescolib_test files
        for i in range(20):
            Path(os.path.join(src_repo_path, str(i))).touch()

        # Set up dataplane for monitoring
        stream_query = f"filerepo_name='{filerepo_name}' AND broadcast"
        dp = setup_dataplane_stream(client, stream_query)

        # Create pipeline configuration
        configparams = json.loads(config_str)

        cadl = {
            'pipeline_id': '0',
            'pipeline_name': str(uuid.uuid1()),
            'nodes': [],
            'edges': []
        }

        # Source node
        params0 = {
            'pluginname': configparams['pluginname'],
            'md5': configparams['md5'],
            'version': configparams['version'],
            'location_region': dst_region,
            'location_agent': dst_agent,
            'filerepo_name': filerepo_name,
            'scan_dir': src_repo_path
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
            'filerepo_name': filerepo_name,
            'repo_dir': dst_repo_path
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
        reply = client.globalcontroller.submit_pipeline(cadl)
        logger.info(f"Status of filerepo pipeline submit: {reply}")

        pipeline_id = reply['gpipeline_id']

        # Wait for pipeline to come online
        wait_for_pipeline(client, pipeline_id)

        # Allow time for synchronization
        logger.info("Waiting for file synchronization...")
        time.sleep(20)

        # Remove pipeline
        logger.info(f"Removing pipeline {pipeline_id}")
        client.globalcontroller.remove_pipeline(pipeline_id)

        # Wait for pipeline to shut down
        wait_for_pipeline(client, pipeline_id, target_status=0)

        logger.info("Single-node file repository pycrescolib_test completed successfully")

    except Exception as e:
        logger.error(f"Error in filerepo_deploy_single_node: {e}", exc_info=True)


def filerepo_deploy_multi_node(client, dst_region: str, dst_agent: str) -> None:
    """Deploy a file repository system across multiple nodes.

    Args:
        client: The Cresco client
        dst_region: Target region (controller)
        dst_agent: Target agent (controller)
    """
    logger.info(f"Starting multi-node file repository deployment with controller at {dst_region}/{dst_agent}")

    # Ensure client is connected
    if not wait_for_connection(client):
        logger.error("Client connection failed, aborting pycrescolib_test")
        return

    # Check controller status
    if not check_controller_active(client, dst_region, dst_agent):
        logger.error("Controller not active, aborting pycrescolib_test")
        return

    try:
        # Download and upload plugin
        jar_file_path = get_plugin_from_git(
            "https://github.com/CrescoEdge/filerepo/releases/download/1.1-SNAPSHOT/filerepo-1.1-SNAPSHOT.jar")
        reply = upload_plugin(client, jar_file_path)

        # Get plugin configuration
        config_str = decompress_param(reply['configparams'])
        logger.info(f"Plugin config: {config_str}")

        # Create unique repository name
        filerepo_name = str(uuid.uuid1())

        # Set up dataplane for monitoring (optional)
        stream_query = f"filerepo_name='{filerepo_name}' AND broadcast"
        logger.info(f"Client stream query: {stream_query}")

        # Create pipeline configuration
        configparams = json.loads(config_str)

        cadl = {
            'pipeline_id': '0',
            'pipeline_name': str(uuid.uuid1()),
            'nodes': [],
            'edges': []
        }

        # Source node (MS4500)
        params0 = {
            'pluginname': configparams['pluginname'],
            'md5': configparams['md5'],
            'version': configparams['version'],
            'persistence_code': '10',
            'location_region': 'lab',
            'location_agent': 'MS4500',
            'filerepo_name': filerepo_name,
            'scan_dir': 'D:\\Analyst Data\\Projects\\TESTING\\A\\Data'
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
            'persistence_code': '10',
            'location_region': 'lab',
            'location_agent': 'controller',
            'filerepo_name': filerepo_name,
            'repo_dir': '\\\\ukhcdata\\dept\\Laboratory Services\\Chandler Clinical Lab\\HLB CoreLabMT\\SPECIAL CHEMISTRY\\RawData\\MS4500\\wiff\\new'
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
        reply = client.globalcontroller.submit_pipeline(cadl)
        logger.info(f"Status of filerepo pipeline submit: {reply}")

        pipeline_id = reply['gpipeline_id']

        # Wait for pipeline to come online
        wait_for_pipeline(client, pipeline_id)

        # Allow time for synchronization
        logger.info("Waiting for file synchronization (2 minutes)...")
        time.sleep(120)

        # Note: Pipeline is not removed in this pycrescolib_test to allow ongoing sync
        logger.info("Multi-node file repository pycrescolib_test completed successfully")

    except Exception as e:
        logger.error(f"Error in filerepo_deploy_multi_node: {e}", exc_info=True)


def filerepo_deploy_multi_node_tox(client, dst_region: str, dst_agent: str) -> None:
    """Deploy a file repository system for toxicology data.

    Args:
        client: The Cresco client
        dst_region: Target region (controller)
        dst_agent: Target agent (controller)
    """
    logger.info(
        f"Starting multi-node toxicology file repository deployment with controller at {dst_region}/{dst_agent}")

    # Ensure client is connected
    if not wait_for_connection(client):
        logger.error("Client connection failed, aborting pycrescolib_test")
        return

    # Check controller status
    if not check_controller_active(client, dst_region, dst_agent):
        logger.error("Controller not active, aborting pycrescolib_test")
        return

    try:
        # Setup logging
        log = setup_logging_stream(client, dst_region, dst_agent)

        # Download and upload plugin
        jar_file_path = get_plugin_from_git(
            "https://github.com/CrescoEdge/filerepo/releases/download/1.1-SNAPSHOT/filerepo-1.1-SNAPSHOT.jar")
        reply = upload_plugin(client, jar_file_path)

        # Get plugin configuration
        config_str = decompress_param(reply['configparams'])

        # Create unique repository name
        filerepo_name = str(uuid.uuid1())

        # Create pipeline configuration
        configparams = json.loads(config_str)

        cadl = {
            'pipeline_id': '0',
            'pipeline_name': str(uuid.uuid1()),
            'nodes': [],
            'edges': []
        }

        # Source node (MS4500)
        params0 = {
            'pluginname': configparams['pluginname'],
            'md5': configparams['md5'],
            'version': configparams['version'],
            'persistence_code': '10',
            'location_region': 'lab',
            'location_agent': 'MS4500',
            'filerepo_name': filerepo_name,
            'scan_dir': 'g:\\2022\\PMDRUG',
            'scan_recursive': 'true'
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
            'persistence_code': '10',
            'location_region': 'lab',
            'location_agent': 'controller',
            'filerepo_name': filerepo_name,
            'repo_dir': '\\\\ukhcdata\\dept\\Laboratory Services\\Chandler Clinical Lab\\HLB CoreLabMT\\SPECIAL CHEMISTRY\\RawData\\MS4500\\PMDRUG'
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
        reply = client.globalcontroller.submit_pipeline(cadl)
        logger.info(f"Status of toxicology filerepo pipeline submit: {reply}")

        pipeline_id = reply['gpipeline_id']

        # Wait for pipeline to come online
        wait_for_pipeline(client, pipeline_id)

        # Allow time for synchronization
        logger.info("Waiting for file synchronization (2 minutes)...")
        time.sleep(120)

        # Note: Pipeline is not removed in this pycrescolib_test to allow ongoing sync
        logger.info("Multi-node toxicology file repository pycrescolib_test completed successfully")

    except Exception as e:
        logger.error(f"Error in filerepo_deploy_multi_node_tox: {e}", exc_info=True)


def filerepo_deploy_multi_node_plugin(client, dst_region: str, dst_agent: str) -> None:
    """Deploy file repository plugins across multiple nodes.

    Args:
        client: The Cresco client
        dst_region: Target region
        dst_agent: Target agent
    """
    logger.info(f"Starting multi-node file repository plugin deployment with controller at {dst_region}/{dst_agent}")

    # Ensure client is connected
    if not wait_for_connection(client):
        logger.error("Client connection failed, aborting pycrescolib_test")
        return

    # Check controller status
    if not check_controller_active(client, dst_region, dst_agent):
        logger.error("Controller not active, aborting pycrescolib_test")
        return

    try:
        # Download and upload plugin
        jar_file_path = get_plugin_from_git(
            "https://github.com/CrescoEdge/filerepo/releases/download/1.1-SNAPSHOT/filerepo-1.1-SNAPSHOT.jar")
        reply = upload_plugin(client, jar_file_path)

        # Get plugin configuration
        config_str = decompress_param(reply['configparams'])

        # Create file repository name
        filerepo_name = 'autopathworker'

        # Set up dataplane
        stream_query = f"filerepo_name='{filerepo_name}' AND broadcast"
        dp = setup_dataplane_stream(client, stream_query)

        # Extract configuration parameters
        configparams = json.loads(config_str)

        # Setup Node 0 - Source node
        node0_dst_region = 'dp'
        node0_dst_agent = 'node0'
        node0_configparams = configparams.copy()
        node0_configparams["filerepo_name"] = filerepo_name
        node0_configparams["scan_dir"] = '/Users/cody/Downloads/node0'
        node0_configparams["scan_recursive"] = 'false'
        node0_configparams["enable_scan"] = 'false'

        reply = client.agents.add_plugin_agent(node0_dst_region, node0_dst_agent, node0_configparams, None)
        logger.info(f"Node 0 plugin added: {reply}")
        node0_repo_plugin_id = reply['pluginid']

        # Wait for node 0 plugin to start
        while client.agents.status_plugin_agent(node0_dst_region, node0_dst_agent, node0_repo_plugin_id)[
            'status_code'] != '10':
            logger.info("Waiting for Node 0 plugin to start...")
            time.sleep(1)

        # Setup Node 1 - Destination node
        node1_dst_region = 'dp'
        node1_dst_agent = 'node1'
        node1_configparams = configparams.copy()
        node1_configparams["filerepo_name"] = filerepo_name
        node1_configparams["scan_dir"] = '/Users/cody/Downloads/node1'
        node1_configparams["scan_recursive"] = 'false'
        node1_configparams["enable_scan"] = 'false'

        reply = client.agents.add_plugin_agent(node1_dst_region, node1_dst_agent, node1_configparams, None)
        logger.info(f"Node 1 plugin added: {reply}")
        node1_repo_plugin_id = reply['pluginid']

        # Wait for node 1 plugin to start
        while client.agents.status_plugin_agent(node1_dst_region, node1_dst_agent, node1_repo_plugin_id)[
            'status_code'] != '10':
            logger.info("Waiting for Node 1 plugin to start...")
            time.sleep(1)

        # Allow time for plugins to initialize
        time.sleep(10)

        # Test file transfer from node0 to node1
        message_event_type = 'EXEC'
        message_payload = {
            'action': 'putfilesremote',
            'dst_region': 'dp',
            'dst_agent': 'node1',
            'dst_plugin': node1_repo_plugin_id,
            'repo_name': filerepo_name,
            'file_list': compress_param(json.dumps(['/Users/cody/Downloads/node0/1']))
        }

        result = client.messaging.global_plugin_msgevent(
            True, message_event_type, message_payload, 'dp', 'node0', node0_repo_plugin_id)
        logger.info(f"File transfer result: {result}")

        # Check file list on node1
        message_event_type = 'EXEC'
        message_payload = {
            'action': 'getrepofilelist',
            'repo_name': filerepo_name
        }

        result = client.messaging.global_plugin_msgevent(
            True, message_event_type, message_payload, 'dp', 'node1', node1_repo_plugin_id)
        repolist = decompress_param(result['repofilelist'])
        logger.info(f"Node1 repository file list: {repolist}")

        # Test file removal on node1
        message_event_type = 'EXEC'
        message_payload = {
            'action': 'removefile',
            'repo_name': filerepo_name,
            'file_name': '1'
        }

        result = client.messaging.global_plugin_msgevent(
            True, message_event_type, message_payload, 'dp', 'node1', node1_repo_plugin_id)
        logger.info(f"File removal result: {result}")

        # Check file list again to confirm removal
        message_event_type = 'EXEC'
        message_payload = {
            'action': 'getrepofilelist',
            'repo_name': filerepo_name
        }

        result = client.messaging.global_plugin_msgevent(
            True, message_event_type, message_payload, 'dp', 'node1', node1_repo_plugin_id)
        repolist = decompress_param(result['repofilelist'])
        logger.info(f"Node1 repository file list after removal: {repolist}")

        logger.info("Multi-node file repository plugin pycrescolib_test completed successfully")

    except Exception as e:
        logger.error(f"Error in filerepo_deploy_multi_node_plugin: {e}", exc_info=True)


# ===== EXECUTOR TESTS =====

def executor_deploy_single_node_pipeline(client, dst_region: str, dst_agent: str) -> None:
    """Deploy an executor service in a pipeline on a single node.

    Args:
        client: The Cresco client
        dst_region: Target region
        dst_agent: Target agent
    """
    logger.info(f"Starting single-node executor pipeline deployment on {dst_region}/{dst_agent}")

    # Ensure client is connected
    if not wait_for_connection(client):
        logger.error("Client connection failed, aborting pycrescolib_test")
        return

    # Check controller status
    if not check_controller_active(client, dst_region, dst_agent):
        logger.error("Controller not active, aborting pycrescolib_test")
        return

    try:
        # Setup logging
        log = setup_logging_stream(client, dst_region, dst_agent)

        # Download and upload plugin
        jar_file_path = get_plugin_from_git(
            "https://github.com/CrescoEdge/executor/releases/download/1.1-SNAPSHOT/executor-1.1-SNAPSHOT.jar")
        reply = upload_plugin(client, jar_file_path)

        # Get plugin configuration
        config_str = decompress_param(reply['configparams'])
        logger.info(f"Plugin config: {config_str}")

        # Create stream name for dataplane
        stream_name = str(uuid.uuid1())

        # Set up dataplane
        stream_query = f"stream_name='{stream_name}'"
        dp = setup_dataplane_stream(client, stream_query)

        # Create pipeline configuration
        configparams = json.loads(config_str)

        cadl = {
            'pipeline_id': '0',
            'pipeline_name': str(uuid.uuid1()),
            'nodes': [],
            'edges': []
        }

        # Executor node
        params0 = {
            'pluginname': configparams['pluginname'],
            'md5': configparams['md5'],
            'version': configparams['version'],
            'location_region': dst_region,
            'location_agent': dst_agent
            # Note: We don't configure stream_name or command here
            # Will be configured via messaging later
        }

        node0 = {
            'type': 'dummy',
            'node_name': 'SRC Plugin',
            'node_id': 0,
            'isSource': False,
            'workloadUtil': 0,
            'params': params0
        }

        cadl['nodes'].append(node0)

        # Submit pipeline
        reply = client.globalcontroller.submit_pipeline(cadl)
        logger.info(f"Status of executor pipeline submit: {reply}")

        pipeline_id = reply['gpipeline_id']

        # Wait for pipeline to come online
        wait_for_pipeline(client, pipeline_id)

        # Get the plugin ID of the executor plugin
        executor_plugin_id = client.globalcontroller.get_pipeline_info(pipeline_id)['nodes'][0]['node_id']
        logger.info(f"Executor plugin ID: {executor_plugin_id}")

        # Send config message to executor plugin
        message_event_type = 'CONFIG'
        message_payload = {
            'action': 'config_process',
            'stream_name': stream_name,
            'command': 'ls -la'  # Adjust for Windows vs Linux
        }

        result = client.messaging.global_plugin_msgevent(
            True, message_event_type, message_payload, dst_region, dst_agent, executor_plugin_id)
        logger.info(f"Config result: {result}")
        logger.info(f"Config status: {result.get('config_status', 'unknown')}")

        # Start process
        message_payload['action'] = 'start_process'
        result = client.messaging.global_plugin_msgevent(
            True, message_event_type, message_payload, dst_region, dst_agent, executor_plugin_id)
        logger.info(f"Start status: {result.get('start_status', 'unknown')}")

        # Wait for output to appear in dataplane
        logger.info("Waiting for command to complete...")
        time.sleep(5)

        # End process
        message_payload['action'] = 'end_process'
        result = client.messaging.global_plugin_msgevent(
            True, message_event_type, message_payload, dst_region, dst_agent, executor_plugin_id)
        logger.info(f"End status: {result.get('end_status', 'unknown')}")

        # Remove pipeline
        logger.info(f"Removing pipeline {pipeline_id}")
        client.globalcontroller.remove_pipeline(pipeline_id)

        # Wait for pipeline to shut down
        wait_for_pipeline(client, pipeline_id, target_status=0)

        logger.info("Single-node executor pipeline pycrescolib_test completed successfully")

    except Exception as e:
        logger.error(f"Error in executor_deploy_single_node_pipeline: {e}", exc_info=True)


def executor_deploy_single_node_plugin(client, dst_region: str, dst_agent: str) -> None:
    """Deploy an executor service as a standalone plugin.

    Args:
        client: The Cresco client
        dst_region: Target region
        dst_agent: Target agent
    """
    logger.info(f"Starting single-node executor plugin deployment on {dst_region}/{dst_agent}")

    # Ensure client is connected
    if not wait_for_connection(client):
        logger.error("Client connection failed, aborting pycrescolib_test")
        return

    # Check controller status
    if not check_controller_active(client, dst_region, dst_agent):
        logger.error("Controller not active, aborting pycrescolib_test")
        return

    try:
        # Download and upload plugin
        jar_file_path = get_plugin_from_git(
            "https://github.com/CrescoEdge/executor/releases/download/1.1-SNAPSHOT/executor-1.1-SNAPSHOT.jar")
        reply = upload_plugin(client, jar_file_path)

        # Get plugin configuration
        config_str = decompress_param(reply['configparams'])

        # Create stream name for dataplane
        stream_name = str(uuid.uuid1())

        # Set up dataplane
        stream_query = f"stream_name='{stream_name}'"
        logger.info(f"Client stream query: {stream_query}")
        dp = setup_dataplane_stream(client, stream_query)

        # Extract configuration parameters
        configparams = json.loads(config_str)

        # Add plugin to agent
        reply = client.agents.add_plugin_agent(dst_region, dst_agent, configparams, None)
        logger.info(f"Executor plugin added: {reply}")
        executor_plugin_id = reply['pluginid']

        # Wait for plugin to start
        while client.agents.status_plugin_agent(dst_region, dst_agent, executor_plugin_id)['status_code'] != '10':
            logger.info("Waiting for executor plugin to start...")
            time.sleep(1)

        # Send config message to executor plugin
        message_event_type = 'CONFIG'
        message_payload = {
            'action': 'config_process',
            'stream_name': stream_name,
            'command': 'dir "C:\\Users\\cornerstone"'  # Adjust for Windows vs Linux
        }

        result = client.messaging.global_plugin_msgevent(
            True, message_event_type, message_payload, dst_region, dst_agent, executor_plugin_id)
        logger.info(f"Config result: {result}")
        logger.info(f"Config status: {result.get('config_status', 'unknown')}")

        # Start process
        message_payload['action'] = 'start_process'
        result = client.messaging.global_plugin_msgevent(
            True, message_event_type, message_payload, dst_region, dst_agent, executor_plugin_id)
        logger.info(f"Start status: {result.get('start_status', 'unknown')}")

        # Wait for output to appear in dataplane
        logger.info("Waiting for command to complete...")
        time.sleep(5)

        # End process
        message_payload['action'] = 'end_process'
        result = client.messaging.global_plugin_msgevent(
            True, message_event_type, message_payload, dst_region, dst_agent, executor_plugin_id)
        logger.info(f"End result: {result}")
        logger.info(f"End status: {result.get('end_status', 'unknown')}")

        # Remove plugin
        logger.info(f"Removing plugin {executor_plugin_id}")
        client.agents.remove_plugin_agent(dst_region, dst_agent, executor_plugin_id)

        # Wait for plugin to shut down
        while client.agents.status_plugin_agent(dst_region, dst_agent, executor_plugin_id)['status_code'] == '10':
            logger.info("Waiting for plugin to shut down...")
            time.sleep(1)

        logger.info("Single-node executor plugin pycrescolib_test completed successfully")

    except Exception as e:
        logger.error(f"Error in executor_deploy_single_node_plugin: {e}", exc_info=True)


def interactive_executor_deploy_single_node_plugin(client, dst_region: str, dst_agent: str) -> None:
    """Deploy an interactive executor service.

    Args:
        client: The Cresco client
        dst_region: Target region
        dst_agent: Target agent
    """
    logger.info(f"Starting interactive executor deployment on {dst_region}/{dst_agent}")

    # Ensure client is connected
    if not wait_for_connection(client):
        logger.error("Client connection failed, aborting pycrescolib_test")
        return

    # Check controller status
    if not check_controller_active(client, dst_region, dst_agent):
        logger.error("Controller not active, aborting pycrescolib_test")
        return

    try:
        # Create identifiers for dataplane
        ident_key = 'stream_name'
        ident_id = str(uuid.uuid1())

        # Set up dataplane configuration
        config_dp = {
            'ident_key': ident_key,
            'ident_id': ident_id,
            'io_type_key': 'type',
            'output_id': 'output',
            'input_id': 'input'
        }

        # Set up dataplane
        dp = setup_dataplane_stream(client, json.dumps(config_dp))

        # Download and upload plugin
        jar_file_path = get_plugin_from_git(
            "https://github.com/CrescoEdge/executor/releases/download/1.1-SNAPSHOT/executor-1.1-SNAPSHOT.jar")
        reply = upload_plugin(client, jar_file_path)

        # Extract configuration parameters
        configparams = json.loads(decompress_param(reply['configparams']))

        # Add plugin to agent
        reply = client.agents.add_plugin_agent(dst_region, dst_agent, configparams, None)
        logger.info(f"Interactive executor plugin added: {reply}")
        executor_plugin_id = reply['pluginid']

        # Wait for plugin to start
        while client.agents.status_plugin_agent(dst_region, dst_agent, executor_plugin_id)['status_code'] != '10':
            logger.info("Waiting for executor plugin to start...")
            time.sleep(1)

        # Send config message for interactive mode
        message_event_type = 'CONFIG'
        message_payload = {
            'action': 'config_process',
            'stream_name': ident_id,
            'command': '-interactive-'
        }

        result = client.messaging.global_plugin_msgevent(
            True, message_event_type, message_payload, dst_region, dst_agent, executor_plugin_id)
        logger.info(f"Config result: {result}")
        logger.info(f"Config status: {result.get('config_status', 'unknown')}")

        # Start process
        message_payload['action'] = 'start_process'
        result = client.messaging.global_plugin_msgevent(
            True, message_event_type, message_payload, dst_region, dst_agent, executor_plugin_id)
        logger.info(f"Start status: {result.get('start_status', 'unknown')}")

        # Check status
        message_payload['action'] = 'status_process'
        result = client.messaging.global_plugin_msgevent(
            True, message_event_type, message_payload, dst_region, dst_agent, executor_plugin_id)
        logger.info(f"Status result: {result}")

        # Interactive shell simulation
        logger.info("Starting interactive shell simulation...")
        commands = [
            "echo Hello from interactive shell",
            "pwd",
            "ls -la",
            "echo End of demonstration",
            "-exit"
        ]

        for cmd in commands:
            logger.info(f"Sending command: {cmd}")
            dp.send(cmd)
            time.sleep(1)

        # End process
        message_payload['action'] = 'end_process'
        result = client.messaging.global_plugin_msgevent(
            True, message_event_type, message_payload, dst_region, dst_agent, executor_plugin_id)
        logger.info(f"End result: {result}")
        logger.info(f"End status: {result.get('end_status', 'unknown')}")

        # Remove plugin
        logger.info(f"Removing plugin {executor_plugin_id}")
        client.agents.remove_plugin_agent(dst_region, dst_agent, executor_plugin_id)

        # Wait for plugin to shut down
        while client.agents.status_plugin_agent(dst_region, dst_agent, executor_plugin_id)['status_code'] == '10':
            logger.info("Waiting for plugin to shut down...")
            time.sleep(1)

        logger.info("Interactive executor pycrescolib_test completed successfully")

    except Exception as e:
        logger.error(f"Error in interactive_executor_deploy_single_node_plugin: {e}", exc_info=True)


# ===== AI API TESTS =====

def aiapi_deploy_single_node_plugin(client, dst_region: str, dst_agent: str) -> None:
    """Deploy an AI API service.

    Args:
        client: The Cresco client
        dst_region: Target region (derived from API)
        dst_agent: Target agent (derived from API)
    """
    logger.info(f"Starting AI API deployment on {dst_region}/{dst_agent}")

    # Ensure client is connected
    if not wait_for_connection(client):
        logger.error("Client connection failed, aborting pycrescolib_test")
        return

    # Check controller status
    global_region = client.api.get_global_region()
    global_agent = client.api.get_global_agent()

    if not check_controller_active(client, global_region, global_agent):
        logger.error("Global controller not active, aborting pycrescolib_test")
        return

    try:
        # Use path to local JAR file
        jar_file_path = '/Users/cody/IdeaProjects/aiapi/target/aiapi-1.1-SNAPSHOT.jar'
        reply = upload_plugin(client, jar_file_path)

        # Extract configuration parameters
        configparams = json.loads(decompress_param(reply['configparams']))

        # Add plugin to agent
        logger.info(f"Adding plugin to agent {dst_region}/{dst_agent}")
        reply = client.agents.add_plugin_agent(dst_region, dst_agent, configparams, None)
        logger.info(f"AI API plugin added: {reply}")
        dst_plugin = reply['pluginid']

        # Wait for plugin to start
        while client.agents.status_plugin_agent(dst_region, dst_agent, dst_plugin)['status_code'] != '10':
            logger.info("Waiting for AI API plugin to start...")
            time.sleep(1)

        logger.info("Plugin deployed successfully")
        time.sleep(2)

        # Example of LLM adapter retrieval
        message_event_type = 'EXEC'
        message_payload = {
            'action': 'getllmadapter',
            's3_access_key': 'rHUYeAk58Ilhg6iUEFtr',
            's3_secret_key': 'IVimdW7BIQLq9PLyVpXzZUq8zS4nLfrsoiZSJanu',
            's3_url': 'http://localhost:9000',
            's3_bucket': 'llmadapters',
            's3_key': 'data/llm_factory_trainer/trainer_template_v0.efe93f27cbc844d78132a3994b6fe6a8/artifacts/adapter/custom_adapter.zip',
            'local_path': 'efe93f27cbc844d78132a3994b6fe6a8.zip'
        }

        logger.info(f"Sending message to {dst_region}/{dst_agent}/{dst_plugin}")
        logger.info(f"Message payload: {message_payload}")

        reply = client.messaging.global_plugin_msgevent(
            True, message_event_type, message_payload, dst_region, dst_agent, dst_plugin)

        logger.info(f"API response: {reply}")

        # Clean up - remove plugin
        logger.info(f"Removing plugin {dst_plugin}")
        client.agents.remove_plugin_agent(dst_region, dst_agent, dst_plugin)

        # Wait for plugin to shut down
        while client.agents.status_plugin_agent(dst_region, dst_agent, dst_plugin)['status_code'] == '10':
            logger.info("Waiting for plugin to shut down...")
            time.sleep(1)

        logger.info("AI API pycrescolib_test completed successfully")

    except Exception as e:
        logger.error(f"Error in aiapi_deploy_single_node_plugin: {e}", exc_info=True)


# ===== UTILITY FUNCTIONS =====

def debug_agent(client, dst_region: str, dst_agent: str) -> None:
    """Debug an agent with enhanced logging and monitoring.

    Args:
        client: The Cresco client
        dst_region: Target region
        dst_agent: Target agent
    """
    logger.info(f"Starting agent debugging for {dst_region}/{dst_agent}")

    # Ensure client is connected
    if not wait_for_connection(client):
        logger.error("Client connection failed, aborting pycrescolib_test")
        return

    # Check controller status
    if not check_controller_active(client, dst_region, dst_agent):
        logger.error("Controller not active, aborting pycrescolib_test")
        return

    try:
        # Setup logging with trace level for activemq components
        log = client.get_logstreamer(lambda msg: logger.debug(f"Log: {msg}"))
        log.connect()

        # Enable detailed logging for ActiveMQ components
        log.update_config_class(dst_region, dst_agent, 'Trace', 'org.apache.activemq')
        log.update_config_class(dst_region, dst_agent, 'Trace', 'org.apache.activemq.*')
        log.update_config_class(dst_region, dst_agent, 'Trace', 'org.apache.activemq.spring')
        log.update_config_class(dst_region, dst_agent, 'Trace', 'org.apache.activemq.broker')

        # Set up dataplane for monitoring
        ident_key = 'stream_name'
        ident_id = '1234'

        config_dp = {
            'ident_key': ident_key,
            'ident_id': ident_id,
            'io_type_key': 'type',
            'output_id': 'output',
            'input_id': 'output'
        }

        json_config = json.dumps(config_dp)
        logger.info(f"Dataplane config: {json_config}")

        dp = setup_dataplane_stream(client, json_config)

        # Monitor indefinitely (until interrupted)
        logger.info("Agent debugging started. Press Ctrl+C to stop...")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Debugging interrupted by user")

        logger.info("Agent debugging completed")

    except Exception as e:
        logger.error(f"Error in debug_agent: {e}", exc_info=True)


def upgrade_controller_plugin(client, dst_region: str, dst_agent: str, jar_file_path: str) -> None:
    """Upgrade a controller plugin.

    Args:
        client: The Cresco client
        dst_region: Target region
        dst_agent: Target agent
        jar_file_path: Path to the JAR file
    """
    logger.info(f"Starting controller plugin upgrade for {dst_region}/{dst_agent}")

    # Ensure client is connected
    if not wait_for_connection(client):
        logger.error("Client connection failed, aborting pycrescolib_test")
        return

    try:
        # Setup logging
        log = setup_logging_stream(client, dst_region, dst_agent)

        # Upload JAR to agent
        logger.info(f"Uploading JAR file {jar_file_path} to agent")
        reply = client.agents.upload_plugin_agent(dst_region, dst_agent, jar_file_path)
        logger.info(f"Upload result: {reply}")

        # Update controller if JAR is uploaded successfully
        if reply.get('is_updated'):
            remote_jar_file_path = reply['jar_file_path']
            logger.info(f"Updating agent with remote JAR: {remote_jar_file_path}")
            client.agents.update_plugin_agent(dst_region, dst_agent, remote_jar_file_path)
            logger.info("Controller plugin update initiated")
        else:
            logger.warning("JAR upload did not result in an update")

        logger.info("Controller plugin upgrade completed")

    except Exception as e:
        logger.error(f"Error in upgrade_controller_plugin: {e}", exc_info=True)


def remove_dead_plugins2(client, dst_region: str, dst_agent: str) -> None:
    """Remove plugins that are no longer active.

    Args:
        client: The Cresco client
        dst_region: Target region
        dst_agent: Target agent
    """
    logger.info(f"Starting dead plugin removal for region {dst_region}")

    # Ensure client is connected
    if not wait_for_connection(client):
        logger.error("Client connection failed, aborting pycrescolib_test")
        return

    # Check controller status
    if not check_controller_active(client, dst_region, dst_agent):
        logger.error("Controller not active, aborting pycrescolib_test")
        return

    try:
        # Get all agents in the region
        agents = client.globalcontroller.get_agent_list(dst_region)
        logger.info(f"Found {len(agents)} agents in region {dst_region}")

        # Check each agent for plugins to remove
        for agent in agents:
            agent_name = agent['name']
            logger.info(f"Checking agent: {agent_name}")

            # Get plugin list for this agent
            try:
                reply = client.agents.list_plugin_agent(dst_region, agent_name)

                # Look for filerepo plugins to remove
                for plugin in reply:
                    if plugin['pluginname'] == 'io.cresco.filerepo':
                        plugin_id = plugin['plugin_id']
                        logger.info(f"Removing filerepo plugin {plugin_id} from {agent_name}")

                        response = client.agents.remove_plugin_agent(dst_region, dst_agent, plugin_id)
                        logger.info(f"Removal response: {response}")
            except Exception as e:
                logger.error(f"Error listing plugins for agent {agent_name}: {e}")

        logger.info("Dead plugin removal completed")

    except Exception as e:
        logger.error(f"Error in remove_dead_plugins2: {e}", exc_info=True)

