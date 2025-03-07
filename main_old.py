"""
Main application for interacting with Cresco framework.
Uses improved client library with proper event loop management.
"""
import json
import logging
import sys
from contextlib import contextmanager

from pycrescolib.clientlib import clientlib, configure_logging

from Testers import (
    filerepo_deploy_single_node, filerepo_deploy_multi_node, debug_agent,
    executor_deploy_single_node_pipeline, executor_deploy_single_node_plugin,
    upgrade_controller_plugin, remove_dead_plugins2, filerepo_deploy_multi_node_tox,
    filerepo_deploy_multi_node_rec, filerepo_deploy_multi_node_plugin,
    pathworker_executor_deploy_single_node_plugin, interactive_executor_deploy_single_node_plugin,
    filerepo_deploy_multi_node_tox_results, interactive_executor_deploy_single_node_plugin_pushonly,
    aiapi_deploy_single_node_plugin
)

# Configure logging
logger = logging.getLogger(__name__)


def setup_logging(level=logging.INFO):
    """Set up logging configuration for the application."""
    # Configure the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)

    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)

    # Add handler to root logger if not already present
    if not root_logger.handlers:
        root_logger.addHandler(console_handler)

    # Configure library logging
    configure_logging(level)

    logger.debug("Logging configured")

def get_agent_list(client, dst_region, dst_agent):
    """Get and display agent list from controller."""
    try:
        # Print status of the global controller
        controller_status = client.agents.get_controller_status(dst_region, dst_agent)
        logger.info(f"Controller status: {controller_status}")
        print(f'Global Controller Status: {controller_status}')

        # If the controller is active continue communication
        if client.agents.is_controller_active(dst_region, dst_agent):
            logger.info(f"Controller {dst_region}/{dst_agent} is active")

            # Get agent list in json form
            reply = client.globalcontroller.get_agent_list()

            # Print agent list
            logger.info(f"Retrieved agent list with {len(reply)} agents")
            print(f'Agent list: {reply}')
            return reply
        else:
            logger.warning(f"Controller {dst_region}/{dst_agent} is not active")
            print(f"Controller {dst_region}/{dst_agent} is not active")
            return None
    except Exception as e:
        logger.error(f"Error getting agent list: {e}")
        print(f"Error getting agent list: {e}")
        return None


def main():
    """Main function to execute pycrescolib_test cases."""
    # Connection parameters
    host = 'localhost'
    port = 8282
    service_key = 'a6f7f889-2500-46d3-9484-5b6499186456'

    logger.info(f"Initializing client for {host}:{port}")

    # Initialize the client
    client = clientlib(host, port, service_key)

    # Test case selection (0 is default)
    test_case = 0

    try:
        # Connect to the server
        if client.connect():
            logger.info("Client connected successfully")
            print('connected')

            try:
                # Default destination is the global controller
                dst_region = 'global-region'
                dst_agent = 'global-controller'

                # Execute selected pycrescolib_test case
                if test_case == 0:
                    # Get a list of agents from a controller
                    get_agent_list(client, dst_region, dst_agent)

                elif test_case == 1:
                    # Filerepo example on a single node
                    logger.info("Running filerepo_deploy_single_node pycrescolib_test case")
                    filerepo_deploy_single_node(client, dst_region, dst_agent)

                elif test_case == 2:
                    # Executor example on a single node pipeline
                    logger.info("Running executor_deploy_single_node_pipeline pycrescolib_test case")
                    executor_deploy_single_node_pipeline(client, dst_region, dst_agent)

                elif test_case == 3:
                    # Multi-node filerepo deployment
                    dst_region = 'lab'
                    dst_agent = 'controller'
                    logger.info(f"Running filerepo_deploy_multi_node pycrescolib_test case on {dst_region}/{dst_agent}")
                    filerepo_deploy_multi_node(client, dst_region, dst_agent)

                elif test_case == 4:
                    # Debug agent
                    dst_region = client.api.get_global_region()
                    dst_agent = client.api.get_global_agent()
                    logger.info(f"Running debug_agent pycrescolib_test case on {dst_region}/{dst_agent}")
                    debug_agent(client, dst_region, dst_agent)

                elif test_case == 5:
                    # Executor deploy single node plugin
                    logger.info("Running executor_deploy_single_node_plugin pycrescolib_test case")
                    executor_deploy_single_node_plugin(client, dst_region, dst_agent)

                elif test_case == 6:
                    # Upgrade controller plugin
                    jar_file_path = '/Users/cody/IdeaProjects/controller/target/controller-1.1-SNAPSHOT.jar'
                    logger.info(f"Running upgrade_controller_plugin pycrescolib_test case with JAR: {jar_file_path}")
                    upgrade_controller_plugin(client, dst_region, dst_agent, jar_file_path)

                elif test_case == 7:
                    # Remove dead plugins
                    dst_region = 'lab'
                    dst_agent = 'MS4500'
                    logger.info(f"Running remove_dead_plugins2 pycrescolib_test case on {dst_region}/{dst_agent}")
                    remove_dead_plugins2(client, dst_region, dst_agent)

                elif test_case == 8:
                    # Get agent info
                    logger.info(f"Getting agent info for {dst_region}/{dst_agent}")
                    reply = client.agents.get_agent_info(dst_region, dst_agent)
                    print(reply)

                elif test_case == 9:
                    # Get agent log
                    dst_region = 'lab'
                    dst_agent = 'controller'
                    logger.info(f"Getting agent log for {dst_region}/{dst_agent}")
                    reply = client.agents.get_agent_log(dst_region, dst_agent)
                    print(reply)

                elif test_case == 10:
                    # Executor plugin - custom region/agent
                    dst_region = 'esports'
                    dst_agent = 'agent-acccc65c-cf79-4b9d-9ab5-d238a546c9e2'
                    logger.info(f"Running executor_deploy_single_node_plugin pycrescolib_test case on {dst_region}/{dst_agent}")
                    executor_deploy_single_node_plugin(client, dst_region, dst_agent)

                elif test_case == 11:
                    # Multi-node tox deployment
                    dst_region = 'lab'
                    dst_agent = 'controller'
                    logger.info(f"Running filerepo_deploy_multi_node_tox pycrescolib_test case on {dst_region}/{dst_agent}")
                    filerepo_deploy_multi_node_tox(client, dst_region, dst_agent)

                elif test_case == 12:
                    # Multi-node rec deployment
                    logger.info(f"Running filerepo_deploy_multi_node_rec pycrescolib_test case")
                    filerepo_deploy_multi_node_rec(client, dst_region, dst_agent)

                elif test_case == 13:
                    # Multi-node plugin deployment
                    dst_region = 'dp'
                    dst_agent = 'controller'
                    logger.info(f"Running filerepo_deploy_multi_node_plugin pycrescolib_test case on {dst_region}/{dst_agent}")
                    filerepo_deploy_multi_node_plugin(client, dst_region, dst_agent)

                elif test_case == 14:
                    # Pathworker executor deploy
                    dst_region = 'dp'
                    dst_agent = 'agent-85231c1e-0763-44ea-bbe2-2902b138948e'
                    logger.info(
                        f"Running pathworker_executor_deploy_single_node_plugin pycrescolib_test case on {dst_region}/{dst_agent}")
                    pathworker_executor_deploy_single_node_plugin(client, dst_region, dst_agent)

                elif test_case == 15:
                    # Interactive executor deploy
                    dst_region = client.api.get_global_region()
                    dst_agent = client.api.get_global_agent()
                    logger.info(
                        f"Running interactive_executor_deploy_single_node_plugin pycrescolib_test case on {dst_region}/{dst_agent}")
                    interactive_executor_deploy_single_node_plugin(client, dst_region, dst_agent)

                elif test_case == 16:
                    # Multi-node tox results
                    dst_region = 'lab'
                    dst_agent = 'controller'
                    logger.info(f"Running filerepo_deploy_multi_node_tox_results pycrescolib_test case on {dst_region}/{dst_agent}")
                    filerepo_deploy_multi_node_tox_results(client, dst_region, dst_agent)

                elif test_case == 17:
                    # Interactive executor push only
                    logger.info(f"Running interactive_executor_deploy_single_node_plugin_pushonly pycrescolib_test case")
                    interactive_executor_deploy_single_node_plugin_pushonly(client, dst_region, dst_agent)

                elif test_case == 18:
                    # AI API deploy
                    dst_region = client.api.get_global_region()
                    dst_agent = client.api.get_global_agent()
                    logger.info(f"Running aiapi_deploy_single_node_plugin pycrescolib_test case on {dst_region}/{dst_agent}")
                    aiapi_deploy_single_node_plugin(client, dst_region, dst_agent)

                else:
                    logger.warning(f"Unknown pycrescolib_test case: {test_case}")
                    print(f"Unknown pycrescolib_test case: {test_case}")

            finally:
                # Always close the client when done
                logger.info("Closing client connection")
                client.close()
        else:
            logger.error("Failed to connect to server")
            print("Failed to connect to server")

    except ConnectionError as e:
        logger.error(f"Connection error: {e}")
        print(f"Connection error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"Error: {e}")


if __name__ == "__main__":
    # Set up logging before anything else
    setup_logging(logging.INFO)

    try:
        main()
    except KeyboardInterrupt:
        logger.info("Application terminated by user")
        print("\nApplication terminated by user")
    except Exception as e:
        logger.critical(f"Unhandled exception: {e}", exc_info=True)
        print(f"Critical error: {e}")
        sys.exit(1)