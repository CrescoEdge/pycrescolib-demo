import json
import random
import time
import uuid
import os
import urllib.request

from pycrescolib.utils import compress_param, decompress_param, get_jar_info
from pathlib import Path


def get_plugin_from_git(src_url, force=False):

    dst_file = src_url.rsplit('/', 1)[1]
    dst_path = 'plugins/' + dst_file

    # create location to store downloaded plugins
    if not os.path.exists('plugins'):
        os.makedirs('plugins')

    if force:
        urllib.request.urlretrieve(src_url, dst_path)
    else:
        if not os.path.exists(dst_path):
            print('Downloading ' + dst_path + ' plugin')
            urllib.request.urlretrieve(src_url, dst_path)

    return dst_path

def filerepo_deploy_single_node(client, dst_region, dst_agent):

    #wait if client is not connected
    while not client.connected():
        print('Waiting on client connection')
        time.sleep(10)
        client.connect()

    if client.agents.is_controller_active(dst_region, dst_agent):

        # An optional custom logger callback
        def logger_callback(n):
            print("Custom logger callback Message = " + str(n))

        # Optionally connect to the agent logger stream
        log = client.get_logstreamer(logger_callback)
        log.connect()
        # Enable logging stream, this needs work, should be selectable via class and level
        log.update_config(dst_region, dst_agent)

        print('Global Controller Status: ' + str(client.agents.get_controller_status(dst_region, dst_agent)))

        #upload filerepo plugin to global controller
        jar_file_path = get_plugin_from_git("https://github.com/CrescoEdge/filerepo/releases/download/1.1-SNAPSHOT/filerepo-1.1-SNAPSHOT.jar")
        reply = client.globalcontroller.upload_plugin_global(jar_file_path)
        print("upload status: " + str(reply))
        print("plugin config: " + decompress_param(reply['configparams']))


        # create unique file repo name
        filerepo_name = str(uuid.uuid1())
        # location to sync
        src_repo_path = 'test_data/' + str(uuid.uuid1())
        src_repo_path = os.path.abspath(src_repo_path)
        os.makedirs(src_repo_path)
        print('src_repo_path: ' + src_repo_path)
        # location to store
        dst_repo_path = 'test_data/' + str(uuid.uuid1())
        dst_repo_path = os.path.abspath(dst_repo_path)
        os.makedirs(dst_repo_path)
        print('dst_repo_path: ' + dst_repo_path)

        # create files to replicate
        for i in range(20):
            Path(src_repo_path + '/' + str(i)).touch()

        # describe the dataplane query allowing python client to listen in on filerepo communications
        # this is not needed, but lets us see what is being communicated by the plugins
        stream_query = "filerepo_name='" + filerepo_name + "' AND broadcast"
        print('Client stream query ' + stream_query)
        # create a dataplane listener for incoming data

        # example of an (optional) custom callback to process incoming data from the dataframe
        def dp_callback(n):
            n = json.loads(n)
            print("Custom DP callback Message = " + str(n))
            print("Custom DP callback Message Type = " + str(type(n)))

        print('Connecting to DP')
        dp = client.get_dataplane(stream_query,dp_callback)
        # connect the listener
        dp.connect()

        # node 0 : file repo sender configuration
        # Use base configparams (plugin_name, md5, etc.) that were extracted during plugin upload
        configparams = json.loads(decompress_param(reply['configparams']))

        cadl = dict()
        cadl['pipeline_id'] = '0'
        cadl['pipeline_name'] = str(uuid.uuid1())
        cadl['nodes'] = []
        cadl['edges'] = []

        params0 = dict()
        # Add plugin information
        params0['pluginname'] = configparams['pluginname']
        params0['md5'] = configparams['md5']
        params0['version'] = configparams['version']
        # Add location information
        params0["location_region"] = dst_region
        params0["location_agent"] = dst_agent
        # Add repo name, which is used in the broadcast of state
        params0["filerepo_name"] = filerepo_name
        # Add scan_dir config telling filerepo to be a sender, and sync our local repo
        params0["scan_dir"] = src_repo_path

        node0 = dict()
        node0['type'] = 'dummy'
        node0['node_name'] = 'SRC Plugin'
        node0['node_id'] = 0
        node0['isSource'] = False
        node0['workloadUtil'] = 0
        node0['params'] = params0

        params1 = dict()
        # Add plugin information
        params1['pluginname'] = configparams['pluginname']
        params1['md5'] = configparams['md5']
        params1['version'] = configparams['version']
        # Add location information
        params1["location_region"] = dst_region
        params1["location_agent"] = dst_agent
        # Add repo name, which is used in the broadcast of state
        params1["filerepo_name"] = filerepo_name
        # Add repo_dir config telling filerepo to recv
        params1["repo_dir"] = dst_repo_path

        node1 = dict()
        node1['type'] = 'dummy'
        node1['node_name'] = 'DST Plugin'
        node1['node_id'] = 1
        node1['isSource'] = False
        node1['workloadUtil'] = 0
        node1['params'] = params1

        edge0 = dict()
        edge0['edge_id'] = 0
        edge0['node_from'] = 0
        edge0['node_to'] = 1
        edge0['params'] = dict()

        cadl['nodes'].append(node0)
        cadl['nodes'].append(node1)
        cadl['edges'].append(edge0)


        # Push config and start sending repo plugin
        reply = client.globalcontroller.submit_pipeline(cadl)
        # name of pipeline remove when finished
        print('Status of filerepo pipeline submit: ' + str(reply))

        pipeline_id = reply['gpipeline_id']
        while client.globalcontroller.get_pipeline_status(pipeline_id) != 10:
            print('waiting for pipeline_id: ' + pipeline_id + ' to come online')
            time.sleep(2)



        # wait for sync
        for i in range(20):
            time.sleep(1)

        # remove the pipeline
        client.globalcontroller.remove_pipeline(pipeline_id)

        while client.globalcontroller.get_pipeline_status(pipeline_id) == 10:
            print('waiting for pipeline_id: ' + pipeline_id + ' to shutdown')
            time.sleep(1)


def executor_deploy_single_node_plugin(client, dst_region, dst_agent):

    #wait if client is not connected
    while not client.connected():
        print('Waiting on client connection')
        time.sleep(10)
        client.connect()

    if client.agents.is_controller_active(dst_region, dst_agent):

        # An optional custom logger callback
        def logger_callback(n):
            print("Custom logger callback Message = " + str(n))

        # Optionally connect to the agent logger stream
        #log = client.get_logstreamer(logger_callback)
        #log.connect()
        # Enable logging stream, this needs work, should be selectable via class and level
        #log.update_config(dst_region, dst_agent)

        print('Global Controller Status: ' + str(client.agents.get_controller_status(dst_region, dst_agent)))

        #upload filerepo plugin to global controller
        jar_file_path = get_plugin_from_git("https://github.com/CrescoEdge/executor/releases/download/1.1-SNAPSHOT/executor-1.1-SNAPSHOT.jar")
        reply = client.globalcontroller.upload_plugin_global(jar_file_path)
        print("upload status: " + str(reply))
        print("plugin config: " + decompress_param(reply['configparams']))

        stream_name = str(uuid.uuid1()) #this will be used to get input back from the dataplane

        # describe the dataplane query allowing python client to listen in on filerepo communications
        # this is not needed, but lets us see what is being communicated by the plugins
        stream_query = "stream_name='" + stream_name + "'"
        print('Client stream query ' + stream_query)
        # create a dataplane listener for incoming data


        # example of an (optional) custom callback to write executor output to a file
        def dp_callback(n):

            print("Custom DP callback Message = " + str(n))

        #print('Connecting to DP')
        #dp = client.get_dataplane(stream_query,dp_callback)
        # connect the listener
        #dp.connect()

        # node 0 : file repo sender configuration
        # Use base configparams (plugin_name, md5, etc.) that were extracted during plugin upload
        configparams = json.loads(decompress_param(reply['configparams']))

        plugin_count = 10000
        plugin_list = []

        for x in range(plugin_count):

            reply = client.agents.add_plugin_agent(dst_region, dst_agent, configparams, None)
            plugin_id = reply['pluginid']
            plugin_list.append(plugin_id)
            print('Status of executor plugin submit: ' + str(x) + ' ' + str(reply))

        while not client.agents.status_plugin_agent(dst_region, dst_agent, plugin_id)['isactive']:
            print('waiting for plugin_id: ' + plugin_id + ' to come online')
            time.sleep(2)

        '''
        for plugin_id in plugin_list:

            # this code makes use of a global message to find a specific plugin type, then send a message to that plugin
            # send a config message to setup the config of the executor
            message_event_type = 'CONFIG'
            message_payload = dict()
            message_payload['action'] = 'config_process'
            message_payload['stream_name'] = stream_name
            #adjust for windows vs linux
            message_payload['command'] = 'ls -la'

            result = client.messaging.global_plugin_msgevent(True, message_event_type, message_payload, dst_region, dst_agent, plugin_id)
            print(result)
            print('config status: ' + str(result['config_status']))

            # Now send a message to start the process
            message_payload['action'] = 'start_process'
            message_payload['stream_name'] = stream_name

            result = client.messaging.global_plugin_msgevent(True, message_event_type, message_payload, dst_region,
                                                             dst_agent, plugin_id)
            print('start status: ' + str(result['start_status']))

            # the process might have already ended, but this is also used to cleanup the task
            message_payload['action'] = 'end_process'
            message_payload['stream_name'] = stream_name

            result = client.messaging.global_plugin_msgevent(True, message_event_type, message_payload, dst_region,
                                                             dst_agent, plugin_id)
            print('end status: ' + str(result['end_status']))

        '''
        for plugin_id in plugin_list:
            reply = client.agents.remove_plugin_agent(dst_region, dst_agent, plugin_id)
            print(reply)
            #print(client.agents.status_plugin_agent(dst_region, dst_agent, plugin_id))



def executor_deploy_single_node_pipeline(client, dst_region, dst_agent):

    #wait if client is not connected
    while not client.connected():
        print('Waiting on client connection')
        time.sleep(10)
        client.connect()

    if client.agents.is_controller_active(dst_region, dst_agent):

        # An optional custom logger callback
        def logger_callback(n):
            print("Custom logger callback Message = " + str(n))

        # Optionally connect to the agent logger stream
        log = client.get_logstreamer(logger_callback)
        log.connect()
        # Enable logging stream, this needs work, should be selectable via class and level
        log.update_config(dst_region, dst_agent)

        print('Global Controller Status: ' + str(client.agents.get_controller_status(dst_region, dst_agent)))

        #upload filerepo plugin to global controller
        jar_file_path = get_plugin_from_git("https://github.com/CrescoEdge/executor/releases/download/1.1-SNAPSHOT/executor-1.1-SNAPSHOT.jar")
        reply = client.globalcontroller.upload_plugin_global(jar_file_path)
        print("upload status: " + str(reply))
        print("plugin config: " + decompress_param(reply['configparams']))

        stream_name = str(uuid.uuid1()) #this will be used to get input back from the dataplane

        # describe the dataplane query allowing python client to listen in on filerepo communications
        # this is not needed, but lets us see what is being communicated by the plugins
        stream_query = "stream_name='" + stream_name + "'"
        print('Client stream query ' + stream_query)
        # create a dataplane listener for incoming data


        # example of an (optional) custom callback to write executor output to a file
        def dp_callback(n):

            print("Custom DP callback Message = " + str(n))

        print('Connecting to DP')
        dp = client.get_dataplane(stream_query,dp_callback)
        # connect the listener
        dp.connect()

        # node 0 : file repo sender configuration
        # Use base configparams (plugin_name, md5, etc.) that were extracted during plugin upload
        configparams = json.loads(decompress_param(reply['configparams']))

        cadl = dict()
        cadl['pipeline_id'] = '0'
        cadl['pipeline_name'] = str(uuid.uuid1())
        cadl['nodes'] = []
        cadl['edges'] = []

        params0 = dict()
        # Add plugin information
        params0['pluginname'] = configparams['pluginname']
        params0['md5'] = configparams['md5']
        params0['version'] = configparams['version']
        # Add location information
        params0["location_region"] = dst_region
        params0["location_agent"] = dst_agent

        # We can configure the plugin to run a job on startup, but in this case we will send several commands interactivly
        # Add name of stream for subscription
        #params0["stream_name"] = stream_name
        # Add scan_dir config telling filerepo to be a sender, and sync our local repo
        #params0["command"] = "ls -la"

        node0 = dict()
        node0['type'] = 'dummy'
        node0['node_name'] = 'SRC Plugin'
        node0['node_id'] = 0
        node0['isSource'] = False
        node0['workloadUtil'] = 0
        node0['params'] = params0

        edge0 = dict()

        cadl['nodes'].append(node0)
        #cadl['edges'].append(edge0)


        # Push config and start executor plugin
        reply = client.globalcontroller.submit_pipeline(cadl)
        # name of pipeline remove when finished
        print('Status of executor pipeline submit: ' + str(reply))

        pipeline_id = reply['gpipeline_id']
        while client.globalcontroller.get_pipeline_status(pipeline_id) != 10:
            print('waiting for pipeline_id: ' + pipeline_id + ' to come online')
            time.sleep(2)

        #get the plugin_id of the executor plugin
        executor_plugin_id = client.globalcontroller.get_pipeline_info(pipeline_id)['nodes'][0]['node_id']

        # this code makes use of a global message to find a specific plugin type, then send a message to that plugin
        # send a config message to setup the config of the executor
        message_event_type = 'CONFIG'
        message_payload = dict()
        message_payload['action'] = 'config_process'
        message_payload['stream_name'] = stream_name
        #adjust for windows vs linux
        message_payload['command'] = 'ls -la'

        result = client.messaging.global_plugin_msgevent(True, message_event_type, message_payload, dst_region, dst_agent, executor_plugin_id)
        print(result)
        print('config status: ' + str(result['config_status']))

        # Now send a message to start the process
        message_payload['action'] = 'start_process'
        message_payload['stream_name'] = stream_name

        result = client.messaging.global_plugin_msgevent(True, message_event_type, message_payload, dst_region,
                                                         dst_agent, executor_plugin_id)
        print('start status: ' + str(result['start_status']))

        # the process might have already ended, but this is also used to cleanup the task
        message_payload['action'] = 'end_process'
        message_payload['stream_name'] = stream_name

        result = client.messaging.global_plugin_msgevent(True, message_event_type, message_payload, dst_region,
                                                         dst_agent, executor_plugin_id)
        print('end status: ' + str(result['end_status']))

        # remove the pipeline
        client.globalcontroller.remove_pipeline(pipeline_id)

        while client.globalcontroller.get_pipeline_status(pipeline_id) == 10:
            print('waiting for pipeline_id: ' + pipeline_id + ' to shutdown')
            time.sleep(1)

def executor_deploy_single_node_plugin(client, dst_region, dst_agent):

    #wait if client is not connected
    while not client.connected():
        print('Waiting on client connection')
        time.sleep(10)
        client.connect()

    if client.agents.is_controller_active(dst_region, dst_agent):

        # An optional custom logger callback
        def logger_callback(n):
            print("Custom logger callback Message = " + str(n))

        # Optionally connect to the agent logger stream
        #log = client.get_logstreamer(logger_callback)
        #log.connect()
        # Enable logging stream, this needs work, should be selectable via class and level
        #log.update_config(dst_region, dst_agent)

        print('Global Controller Status: ' + str(client.agents.get_controller_status(dst_region, dst_agent)))

        #upload filerepo plugin to global controller
        jar_file_path = get_plugin_from_git("https://github.com/CrescoEdge/executor/releases/download/1.1-SNAPSHOT/executor-1.1-SNAPSHOT.jar")
        #jar_file_path = '/Users/cody/IdeaProjects/executor/target/executor-1.1-SNAPSHOT.jar'
        reply = client.globalcontroller.upload_plugin_global(jar_file_path)
        #print("upload status: " + str(reply))
        #print("plugin config: " + decompress_param(reply['configparams']))

        stream_name = str(uuid.uuid1()) #this will be used to get input back from the dataplane

        # describe the dataplane query allowing python client to listen in on filerepo communications
        # this is not needed, but lets us see what is being communicated by the plugins
        stream_query = "stream_name='" + stream_name + "'"
        print('Client stream query ' + stream_query)
        # create a dataplane listener for incoming data


        # example of an (optional) custom callback to write executor output to a file
        def dp_callback(n):

            print("Custom DP callback Message = " + str(n))

        print('Connecting to DP')
        dp = client.get_dataplane(stream_query,dp_callback)
        print('Connecting to DP 1')

        # connect the listener
        dp.connect()

        # node 0 : file repo sender configuration
        # Use base configparams (plugin_name, md5, etc.) that were extracted during plugin upload
        configparams = json.loads(decompress_param(reply['configparams']))

        reply = client.agents.add_plugin_agent(dst_region, dst_agent, configparams, None)
        print(reply)
        executor_plugin_id = reply['pluginid']

        while(client.agents.status_plugin_agent(dst_region,dst_agent,executor_plugin_id)['status_code'] != '10'):
            print('waiting on startup')
            time.sleep(1)

        # this code makes use of a global message to find a specific plugin type, then send a message to that plugin
        # send a config message to setup the config of the executor
        message_event_type = 'CONFIG'
        message_payload = dict()
        message_payload['action'] = 'config_process'
        message_payload['stream_name'] = stream_name
        #adjust for windows vs linux
        message_payload['command'] = 'dir "C:\\Users\\cornerstone"'

        result = client.messaging.global_plugin_msgevent(True, message_event_type, message_payload, dst_region, dst_agent, executor_plugin_id)
        print(result)
        print('config status: ' + str(result['config_status']))

        # Now send a message to start the process
        message_payload['action'] = 'start_process'
        message_payload['stream_name'] = stream_name

        result = client.messaging.global_plugin_msgevent(True, message_event_type, message_payload, dst_region,
                                                         dst_agent, executor_plugin_id)
        print('start status: ' + str(result['start_status']))

        time.sleep(5)
        # the process might have already ended, but this is also used to cleanup the task
        message_payload['action'] = 'end_process'
        message_payload['stream_name'] = stream_name

        result = client.messaging.global_plugin_msgevent(True, message_event_type, message_payload, dst_region,
                                                         dst_agent, executor_plugin_id)
        print(result)
        print('end status: ' + str(result['end_status']))

        # remove the pipeline
        client.agents.remove_plugin_agent(dst_region,dst_agent,executor_plugin_id);

        while (client.agents.status_plugin_agent(dst_region, dst_agent, executor_plugin_id)['status_code'] == '10'):
            print('waiting on shutdown')
            print(client.agents.status_plugin_agent(dst_region, dst_agent, executor_plugin_id)['status_code'])
            time.sleep(1)

def pathworker_executor_deploy_single_node_plugin(client, dst_region, dst_agent):

    processmap = dict()

    #wait if client is not connected
    while not client.connected():
        print('Waiting on client connection')
        time.sleep(10)
        client.connect()

    if client.agents.is_controller_active(dst_region, dst_agent):

        # An optional custom logger callback
        def logger_callback(n):
            print("Custom logger callback Message = " + str(n))

        # Optionally connect to the agent logger stream
        #log = client.get_logstreamer(logger_callback)
        #log.connect()
        #1.1.0.SNAPSHOT-2021-12-02T195342Z
        #1.1.0.SNAPSHOT-2021-10-14T175814Z
        # Enable logging stream, this needs work, should be selectable via class and level
        #log.update_config(dst_region, dst_agent)

        print('Global Controller Status: ' + str(client.agents.get_controller_status(dst_region, dst_agent)))

        stream_name = str(uuid.uuid1()) #this will be used to get input back from the dataplane

        # describe the dataplane query allowing python client to listen in on filerepo communications
        # this is not needed, but lets us see what is being communicated by the plugins
        stream_query = "stream_name='" + stream_name + "'"
        print('Client stream query ' + stream_query)
        # create a dataplane listener for incoming data

        # example of an (optional) custom callback to write executor output to a file
        def dp_callback(n):


            try:
                payload = json.loads(str(n))
                print("json payload = " + str(payload))
            except:
                print("Custom DP callback Message = " + str(n))


        print('Connecting to DP ' + stream_query)
        dp = client.get_dataplane(stream_query, dp_callback)

        # connect the listener
        dp.connect()

        # node 0 : file repo sender configuration
        # Use base configparams (plugin_name, md5, etc.) that were extracted during plugin upload
        #configparams = json.loads(decompress_param(reply['configparams']))
        configparams = dict()
        configparams['pluginname'] = 'io.cresco.executor'
        configparams['version'] = '1.1.0.SNAPSHOT-2021-12-02T195342Z'
        configparams['md5'] = '893deca0083ce5e301071577dccfdc9c'


        print(configparams)

        reply = client.agents.add_plugin_agent(dst_region, dst_agent, configparams, None)
        print(reply)
        executor_plugin_id = reply['pluginid']

        while(client.agents.status_plugin_agent(dst_region,dst_agent,executor_plugin_id)['status_code'] != '10'):
            print('waiting on startup')
            time.sleep(1)

        # this code makes use of a global message to find a specific plugin type, then send a message to that plugin
        # send a config message to setup the config of the executor
        message_event_type = 'CONFIG'
        message_payload = dict()
        message_payload['action'] = 'config_process'
        message_payload['stream_name'] = stream_name
        #adjust for windows vs linux
        message_payload['command'] = 'cd /digitalpathprocessor/webapiclient; python3 client.py --test_mode=0'
        #message_payload['command'] = 'cd /digitalpathprocessor/webapiclient; bash test.sh'

        result = client.messaging.global_plugin_msgevent(True, message_event_type, message_payload, dst_region, dst_agent, executor_plugin_id)
        print(result)
        print('config status: ' + str(result['config_status']))

        # Now send a message to start the process
        message_payload['action'] = 'start_process'
        message_payload['stream_name'] = stream_name

        result = client.messaging.global_plugin_msgevent(True, message_event_type, message_payload, dst_region,
                                                         dst_agent, executor_plugin_id)
        print('start status: ' + str(result['start_status']))

        # the process might have already ended, but this is also used to cleanup the task
        message_payload['action'] = 'status_process'
        message_payload['stream_name'] = stream_name

        result = client.messaging.global_plugin_msgevent(True, message_event_type, message_payload, dst_region,
                                                         dst_agent, executor_plugin_id)
        print(result)

        time.sleep(5)

        result = client.messaging.global_plugin_msgevent(True, message_event_type, message_payload, dst_region,
                                                         dst_agent, executor_plugin_id)
        print(result)

        time.sleep(30)

        # the process might have already ended, but this is also used to cleanup the task
        message_payload['action'] = 'end_process'
        message_payload['stream_name'] = stream_name

        result = client.messaging.global_plugin_msgevent(True, message_event_type, message_payload, dst_region,
                                                         dst_agent, executor_plugin_id)
        print(result)
        print('end status: ' + str(result['end_status']))

        # remove the pipeline
        client.agents.remove_plugin_agent(dst_region,dst_agent,executor_plugin_id);

        while (client.agents.status_plugin_agent(dst_region, dst_agent, executor_plugin_id)['status_code'] == '10'):
            print('waiting on shutdown')
            print(client.agents.status_plugin_agent(dst_region, dst_agent, executor_plugin_id)['status_code'])
            time.sleep(1)

def interactive_executor_deploy_single_node_plugin(client, dst_region, dst_agent):

    processmap = dict()

    #wait if client is not connected
    while not client.connected():
        print('Waiting on client connection')
        time.sleep(10)
        client.connect()

    if client.agents.is_controller_active(dst_region, dst_agent):


        print('Global Controller Status: ' + str(client.agents.get_controller_status(dst_region, dst_agent)))

        ident_key = 'stream_name'
        ident_id = str(uuid.uuid1())
        stream_query = "stream_name='" + ident_id + "'"

        config_dp = dict()
        config_dp['ident_key'] = ident_key
        config_dp['ident_id'] = ident_id
        config_dp['io_type_key'] = 'type'
        config_dp['output_id'] = 'output'
        config_dp['input_id'] = 'input'

        # example of an (optional) custom callback to write executor output to a file
        def dp_callback(n):


            try:
                payload = json.loads(str(n))
                print("json payload = " + str(payload))
            except:
                print(str(n))


        print('Connecting to DP ' + stream_query)
        dp = client.get_dataplane(json.dumps(config_dp), dp_callback)

        # connect the listener
        dp.connect()

        jar_file_path = '/Users/cody/IdeaProjects/executor/target/executor-1.1-SNAPSHOT.jar'
        reply = client.globalcontroller.upload_plugin_global(jar_file_path)

        configparams = json.loads(decompress_param(reply['configparams']))

        print(configparams)

        reply = client.agents.add_plugin_agent(dst_region, dst_agent, configparams, None)
        print(reply)
        executor_plugin_id = reply['pluginid']

        while(client.agents.status_plugin_agent(dst_region,dst_agent,executor_plugin_id)['status_code'] != '10'):
            print('waiting on startup')
            time.sleep(1)

        # this code makes use of a global message to find a specific plugin type, then send a message to that plugin
        # send a config message to setup the config of the executor
        message_event_type = 'CONFIG'
        message_payload = dict()
        message_payload['action'] = 'config_process'
        message_payload['stream_name'] = ident_id
        #adjust for windows vs linux
        message_payload['command'] = '-interactive-'
        #message_payload['command'] = 'cd /digitalpathprocessor/webapiclient; bash test.sh'

        result = client.messaging.global_plugin_msgevent(True, message_event_type, message_payload, dst_region, dst_agent, executor_plugin_id)
        print(result)
        print('config status: ' + str(result['config_status']))

        # Now send a message to start the process
        message_payload['action'] = 'start_process'
        message_payload['stream_name'] = ident_id

        result = client.messaging.global_plugin_msgevent(True, message_event_type, message_payload, dst_region,
                                                         dst_agent, executor_plugin_id)
        print('start status: ' + str(result['start_status']))

        # the process might have already ended, but this is also used to cleanup the task
        message_payload['action'] = 'status_process'
        message_payload['stream_name'] = ident_id

        result = client.messaging.global_plugin_msgevent(True, message_event_type, message_payload, dst_region,
                                                         dst_agent, executor_plugin_id)
        print(result)

        value = '1'
        while (not value.startswith('-exit')):
            if dp:
                value = input('cshell# ')
                dp.send(value)
            else:
                print('waiting active')
            time.sleep(1)


        # the process might have already ended, but this is also used to cleanup the task
        message_payload['action'] = 'end_process'
        message_payload['stream_name'] = ident_id

        result = client.messaging.global_plugin_msgevent(True, message_event_type, message_payload, dst_region,
                                                         dst_agent, executor_plugin_id)
        print(result)
        print('end status: ' + str(result['end_status']))

        # remove the pipeline
        client.agents.remove_plugin_agent(dst_region,dst_agent,executor_plugin_id);

        while (client.agents.status_plugin_agent(dst_region, dst_agent, executor_plugin_id)['status_code'] == '10'):
            print('waiting on shutdown')
            print(client.agents.status_plugin_agent(dst_region, dst_agent, executor_plugin_id)['status_code'])
            time.sleep(1)

def interactive_executor_deploy_single_node_plugin_pushonly(client, dst_region, dst_agent):

    processmap = dict()

    #wait if client is not connected
    while not client.connected():
        print('Waiting on client connection')
        time.sleep(10)
        client.connect()

    if client.agents.is_controller_active(dst_region, dst_agent):


        print('Global Controller Status: ' + str(client.agents.get_controller_status(dst_region, dst_agent)))

        ident_id = str(uuid.uuid1())


        jar_file_path = '/Users/cody/IdeaProjects/executor/target/executor-1.1-SNAPSHOT.jar'
        reply = client.globalcontroller.upload_plugin_global(jar_file_path)

        configparams = json.loads(decompress_param(reply['configparams']))

        print(configparams)

        reply = client.agents.add_plugin_agent(dst_region, dst_agent, configparams, None)
        print(reply)
        executor_plugin_id = reply['pluginid']

        while(client.agents.status_plugin_agent(dst_region,dst_agent,executor_plugin_id)['status_code'] != '10'):
            print('waiting on startup')
            time.sleep(1)

        # this code makes use of a global message to find a specific plugin type, then send a message to that plugin
        # send a config message to setup the config of the executor
        message_event_type = 'CONFIG'
        message_payload = dict()
        message_payload['action'] = 'config_process'
        message_payload['stream_name'] = ident_id
        #adjust for windows vs linux
        message_payload['command'] = '-interactive-'

        result = client.messaging.global_plugin_msgevent(True, message_event_type, message_payload, dst_region, dst_agent, executor_plugin_id)
        print(result)
        print('config status: ' + str(result['config_status']))

        # Now send a message to start the process
        message_payload['action'] = 'start_process'
        message_payload['stream_name'] = ident_id

        result = client.messaging.global_plugin_msgevent(True, message_event_type, message_payload, dst_region,
                                                         dst_agent, executor_plugin_id)
        print('start status: ' + str(result['start_status']))

        # the process might have already ended, but this is also used to cleanup the task
        message_payload['action'] = 'status_process'
        message_payload['stream_name'] = ident_id

        result = client.messaging.global_plugin_msgevent(True, message_event_type, message_payload, dst_region,
                                                         dst_agent, executor_plugin_id)
        print(result)




def filerepo_deploy_multi_node_plugin(client, dst_region, dst_agent):

    #wait if client is not connected
    while not client.connected():
        print('Waiting on client connection')
        time.sleep(10)
        client.connect()

    if client.agents.is_controller_active(dst_region, dst_agent):

        # An optional custom logger callback
        def logger_callback(n):
            print("Custom logger callback Message = " + str(n))

        # Optionally connect to the agent logger stream
        #log = client.get_logstreamer(logger_callback)
        #log.connect()
        # Enable logging stream, this needs work, should be selectable via class and level
        #log.update_config(dst_region, dst_agent)

        print('Global Controller Status: ' + str(client.agents.get_controller_status(dst_region, dst_agent)))

        jar_file_path = '/Users/cody/IdeaProjects/filerepo/target/filerepo-1.1-SNAPSHOT.jar'
        reply = client.globalcontroller.upload_plugin_global(jar_file_path)
        print("upload status: " + str(reply))
        print("plugin config: " + decompress_param(reply['configparams']))

        filerepo_name = 'autopathworker'
        # describe the dataplane query allowing python client to listen in on filerepo communications
        # this is not needed, but lets us see what is being communicated by the plugins
        stream_query = "filerepo_name='" + filerepo_name + "' AND broadcast"
        print('Client stream query ' + stream_query)
        # create a dataplane listener for incoming data


        # example of an (optional) custom callback to write executor output to a file
        def dp_callback(n):

            print("Custom DP callback Message = " + str(n))

        dp = client.get_dataplane(stream_query,dp_callback)
        print('Connecting to DP')

        # connect the listener
        dp.connect()

        # Use base configparams (plugin_name, md5, etc.) that were extracted during plugin upload
        configparams = json.loads(decompress_param(reply['configparams']))

        # node 0 : file repo sender configuration
        node0_dst_region = 'dp'
        node0_dst_agent = 'node0'
        node0_configparams = configparams.copy()
        node0_configparams["filerepo_name"] = filerepo_name
        node0_configparams["scan_dir"] = '/Users/cody/Downloads/node0'
        node0_configparams["scan_recursive"] = 'false'
        node0_configparams["enable_scan"] = 'false'

        reply = client.agents.add_plugin_agent(node0_dst_region, node0_dst_agent, node0_configparams, None)
        print(reply)
        node0_repo_plugin_id = reply['pluginid']

        while(client.agents.status_plugin_agent(node0_dst_region,node0_dst_agent,node0_repo_plugin_id)['status_code'] != '10'):
            print('waiting on startup')
            time.sleep(1)

        # node 1 : file repo sender configuration
        node1_dst_region = 'dp'
        node1_dst_agent = 'node1'
        node1_configparams = configparams.copy()
        node1_configparams["filerepo_name"] = filerepo_name
        node1_configparams["scan_dir"] = '/Users/cody/Downloads/node1'
        node1_configparams["scan_recursive"] = 'false'
        node1_configparams["enable_scan"] = 'false'

        reply = client.agents.add_plugin_agent(node1_dst_region, node1_dst_agent, node1_configparams, None)
        print(reply)
        node1_repo_plugin_id = reply['pluginid']

        while (client.agents.status_plugin_agent(node1_dst_region, node1_dst_agent, node1_repo_plugin_id)[
                   'status_code'] != '10'):
            print('waiting on startup')
            time.sleep(1)

        time.sleep(10)


        message_event_type = 'EXEC'
        message_payload = dict()
        message_payload['action'] = 'putfilesremote'
        # adjust for windows vs linux
        message_payload['dst_region'] = 'dp'
        message_payload['dst_agent'] = 'node1'
        message_payload['dst_plugin'] = node1_repo_plugin_id
        message_payload['repo_name'] = filerepo_name
        file_list = ['/Users/cody/Downloads/node0/1']
        message_payload['file_list'] = compress_param(json.dumps(file_list))

        result = client.messaging.global_plugin_msgevent(True, message_event_type, message_payload, 'dp',
                                                         'node0', node0_repo_plugin_id)
        print(result)

        '''
        message_event_type = 'EXEC'
        message_payload = dict()
        message_payload['action'] = 'putfiles'
        # adjust for windows vs linux
        message_payload['dst_region'] = 'dp'
        message_payload['dst_agent'] = 'node1'
        message_payload['dst_plugin'] = node1_repo_plugin_id
        message_payload['repo_name'] = filerepo_name
        file_list = ['/Users/cody/Downloads/node0/1']
        message_payload['file_list'] = compress_param(json.dumps(file_list))
        # print("plugin config: " + decompress_param(result['repolist']))

        result = client.messaging.global_plugin_msgevent(True, message_event_type, message_payload, 'dp',
                                                         'node1', node1_repo_plugin_id)
        '''

        message_event_type = 'EXEC'
        message_payload = dict()
        message_payload['action'] = 'getrepofilelist'
        message_payload['repo_name'] = filerepo_name

        result = client.messaging.global_plugin_msgevent(True, message_event_type, message_payload, 'dp',
                                                         'node1', node1_repo_plugin_id)
        # print(result)
        repolist = decompress_param(result['repofilelist'])
        print(repolist)

        time.sleep(10)

        message_event_type = 'EXEC'
        message_payload = dict()
        message_payload['action'] = 'removefile'
        message_payload['repo_name'] = filerepo_name
        message_payload['file_name'] = '1'

        result = client.messaging.global_plugin_msgevent(True, message_event_type, message_payload, 'dp',
                                                         'node1', node1_repo_plugin_id)
        print(result)

        while(True):
            message_event_type = 'EXEC'
            message_payload = dict()
            message_payload['action'] = 'getrepofilelist'
            message_payload['repo_name'] = filerepo_name

            result = client.messaging.global_plugin_msgevent(True, message_event_type, message_payload, 'dp',
                                                             'node1', node1_repo_plugin_id)
            #print(result)
            repolist = decompress_param(result['repofilelist'])
            print(repolist)

            time.sleep(1000)




def filerepo_deploy_multi_node(client, dst_region, dst_agent):

    #wait if client is not connected
    while not client.connected():
        print('Waiting on client connection')
        time.sleep(10)
        client.connect()

    if client.agents.is_controller_active(dst_region, dst_agent):

        # An optional custom logger callback
        #def logger_callback(n):
        #    print("Custom logger callback Message = " + str(n))

        # Optionally connect to the agent logger stream
        #log = client.get_logstreamer(logger_callback)
        #log.connect()
        # Enable logging stream, this needs work, should be selectable via class and level
        #log.update_config(dst_region, dst_agent)

        print('Global Controller Status: ' + str(client.agents.get_controller_status(dst_region, dst_agent)))

        #upload filerepo plugin to global controller
        jar_file_path = get_plugin_from_git("https://github.com/CrescoEdge/filerepo/releases/download/1.1-SNAPSHOT/filerepo-1.1-SNAPSHOT.jar")
        reply = client.globalcontroller.upload_plugin_global(jar_file_path)
        print("upload status: " + str(reply))
        print("plugin config: " + decompress_param(reply['configparams']))


        # create unique file repo name
        filerepo_name = str(uuid.uuid1())
        # location to sync
        #src_repo_path = 'test_data/' + str(uuid.uuid1())
        #src_repo_path = os.path.abspath(src_repo_path)
        #os.makedirs(src_repo_path)
        #print('src_repo_path: ' + src_repo_path)
        # location to store
        ##dst_repo_path = 'test_data/' + str(uuid.uuid1())
        #dst_repo_path = os.path.abspath(dst_repo_path)
        #os.makedirs(dst_repo_path)
        #print('dst_repo_path: ' + dst_repo_path)

        # create files to replicate
        #for i in range(20):
        #    Path(src_repo_path + '/' + str(i)).touch()

        # describe the dataplane query allowing python client to listen in on filerepo communications
        # this is not needed, but lets us see what is being communicated by the plugins
        stream_query = "filerepo_name='" + filerepo_name + "' AND broadcast"
        print('Client stream query ' + stream_query)
        # create a dataplane listener for incoming data

        # example of an (optional) custom callback to process incoming data from the dataframe
        def dp_callback(n):
            n = json.loads(n)
            print("Custom DP callback Message = " + str(n))
            print("Custom DP callback Message Type = " + str(type(n)))

        #print('Connecting to DP')
        #dp = client.get_dataplane(stream_query,dp_callback)
        # connect the listener
        #dp.connect()

        # node 0 : file repo sender configuration
        # Use base configparams (plugin_name, md5, etc.) that were extracted during plugin upload
        configparams = json.loads(decompress_param(reply['configparams']))

        cadl = dict()
        cadl['pipeline_id'] = '0'
        cadl['pipeline_name'] = str(uuid.uuid1())
        cadl['nodes'] = []
        cadl['edges'] = []

        params0 = dict()
        # Add plugin information
        params0['pluginname'] = configparams['pluginname']
        params0['md5'] = configparams['md5']
        params0['version'] = configparams['version']
        params0['persistence_code'] = '10'
        # Add location information
        params0["location_region"] = 'lab'
        params0["location_agent"] = 'MS4500'
        # Add repo name, which is used in the broadcast of state
        params0["filerepo_name"] = filerepo_name
        # Add scan_dir config telling filerepo to be a sender, and sync our local repo
        params0["scan_dir"] = 'D:\\Analyst Data\\Projects\\TESTING\\A\\Data'

        node0 = dict()
        node0['type'] = 'dummy'
        node0['node_name'] = 'SRC Plugin'
        node0['node_id'] = 0
        node0['isSource'] = False
        node0['workloadUtil'] = 0
        node0['params'] = params0

        params1 = dict()
        # Add plugin information
        params1['pluginname'] = configparams['pluginname']
        params1['md5'] = configparams['md5']
        params1['version'] = configparams['version']
        params0['persistence_code'] = '10'
        # Add location information
        params1["location_region"] = 'lab'
        params1["location_agent"] = 'controller'
        # Add repo name, which is used in the broadcast of state
        params1["filerepo_name"] = filerepo_name
        # Add repo_dir config telling filerepo to recv
        params1["repo_dir"] = '\\\\ukhcdata\\dept\\Laboratory Services\\Chandler Clinical Lab\\HLB CoreLabMT\\SPECIAL CHEMISTRY\\RawData\\MS4500\\wiff\\new'

        node1 = dict()
        node1['type'] = 'dummy'
        node1['node_name'] = 'DST Plugin'
        node1['node_id'] = 1
        node1['isSource'] = False
        node1['workloadUtil'] = 0
        node1['params'] = params1

        edge0 = dict()
        edge0['edge_id'] = 0
        edge0['node_from'] = 0
        edge0['node_to'] = 1
        edge0['params'] = dict()

        cadl['nodes'].append(node0)
        cadl['nodes'].append(node1)
        cadl['edges'].append(edge0)


        # Push config and start sending repo plugin
        reply = client.globalcontroller.submit_pipeline(cadl)
        # name of pipeline remove when finished
        print('Status of filerepo pipeline submit: ' + str(reply))

        pipeline_id = reply['gpipeline_id']
        while client.globalcontroller.get_pipeline_status(pipeline_id) != 10:
            print('waiting for pipeline_id: ' + pipeline_id + ' to come online')
            time.sleep(2)

        # wait for sync
        for i in range(120):
            time.sleep(1)

        # remove the pipeline
        #client.globalcontroller.remove_pipeline(pipeline_id)

        #while client.globalcontroller.get_pipeline_status(pipeline_id) == 10:
        #    print('waiting for pipeline_id: ' + pipeline_id + ' to shutdown')
        #    time.sleep(1)



def filerepo_deploy_multi_node_tox(client, dst_region, dst_agent):

    #wait if client is not connected
    while not client.connected():
        print('Waiting on client connection')
        time.sleep(10)
        client.connect()

    if client.agents.is_controller_active(dst_region, dst_agent):

        # An optional custom logger callback
        def logger_callback(n):
            print("Custom logger callback Message = " + str(n))

        # Optionally connect to the agent logger stream
        log = client.get_logstreamer(logger_callback)
        log.connect()
        # Enable logging stream, this needs work, should be selectable via class and level
        log.update_config(dst_region, dst_agent)

        print('Global Controller Status: ' + str(client.agents.get_controller_status(dst_region, dst_agent)))

        #upload filerepo plugin to global controller
        jar_file_path = get_plugin_from_git("https://github.com/CrescoEdge/filerepo/releases/download/1.1-SNAPSHOT/filerepo-1.1-SNAPSHOT.jar")
        #jar_file_path = '/Users/cody/IdeaProjects/filerepo/target/filerepo-1.1-SNAPSHOT.jar'
        reply = client.globalcontroller.upload_plugin_global(jar_file_path)
        print("upload status: " + str(reply))
        print("plugin config: " + decompress_param(reply['configparams']))


        # create unique file repo name
        filerepo_name = str(uuid.uuid1())
        # location to sync
        #src_repo_path = 'test_data/' + str(uuid.uuid1())
        #src_repo_path = os.path.abspath(src_repo_path)
        #os.makedirs(src_repo_path)
        #print('src_repo_path: ' + src_repo_path)
        # location to store
        ##dst_repo_path = 'test_data/' + str(uuid.uuid1())
        #dst_repo_path = os.path.abspath(dst_repo_path)
        #os.makedirs(dst_repo_path)
        #print('dst_repo_path: ' + dst_repo_path)

        # create files to replicate
        #for i in range(20):
        #    Path(src_repo_path + '/' + str(i)).touch()

        # describe the dataplane query allowing python client to listen in on filerepo communications
        # this is not needed, but lets us see what is being communicated by the plugins
        stream_query = "filerepo_name='" + filerepo_name + "' AND broadcast"
        print('Client stream query ' + stream_query)
        # create a dataplane listener for incoming data

        # example of an (optional) custom callback to process incoming data from the dataframe
        def dp_callback(n):
            n = json.loads(n)
            print("Custom DP callback Message = " + str(n))
            print("Custom DP callback Message Type = " + str(type(n)))

        #print('Connecting to DP')
        #dp = client.get_dataplane(stream_query,dp_callback)
        # connect the listener
        #dp.connect()

        # node 0 : file repo sender configuration
        # Use base configparams (plugin_name, md5, etc.) that were extracted during plugin upload
        configparams = json.loads(decompress_param(reply['configparams']))

        cadl = dict()
        cadl['pipeline_id'] = '0'
        cadl['pipeline_name'] = str(uuid.uuid1())
        cadl['nodes'] = []
        cadl['edges'] = []

        params0 = dict()
        # Add plugin information
        params0['pluginname'] = configparams['pluginname']
        params0['md5'] = configparams['md5']
        params0['version'] = configparams['version']
        params0['persistence_code'] = '10'
        # Add location information
        params0["location_region"] = 'lab'
        params0["location_agent"] = 'MS4500'
        # Add repo name, which is used in the broadcast of state
        params0["filerepo_name"] = filerepo_name
        # Add scan_dir config telling filerepo to be a sender, and sync our local repo
        params0["scan_dir"] = 'g:\\2022\\PMDRUG'
        params0["scan_recursive"] = 'true'

        node0 = dict()
        node0['type'] = 'dummy'
        node0['node_name'] = 'SRC Plugin'
        node0['node_id'] = 0
        node0['isSource'] = False
        node0['workloadUtil'] = 0
        node0['params'] = params0

        params1 = dict()
        # Add plugin information
        params1['pluginname'] = configparams['pluginname']
        params1['md5'] = configparams['md5']
        params1['version'] = configparams['version']
        params0['persistence_code'] = '10'
        # Add location information
        params1["location_region"] = 'lab'
        params1["location_agent"] = 'controller'
        # Add repo name, which is used in the broadcast of state
        params1["filerepo_name"] = filerepo_name
        # Add repo_dir config telling filerepo to recv
        params1["repo_dir"] = '\\\\ukhcdata\\dept\\Laboratory Services\\Chandler Clinical Lab\\HLB CoreLabMT\\SPECIAL CHEMISTRY\\RawData\\MS4500\\PMDRUG'

        node1 = dict()
        node1['type'] = 'dummy'
        node1['node_name'] = 'DST Plugin'
        node1['node_id'] = 1
        node1['isSource'] = False
        node1['workloadUtil'] = 0
        node1['params'] = params1

        edge0 = dict()
        edge0['edge_id'] = 0
        edge0['node_from'] = 0
        edge0['node_to'] = 1
        edge0['params'] = dict()

        cadl['nodes'].append(node0)
        cadl['nodes'].append(node1)
        cadl['edges'].append(edge0)


        # Push config and start sending repo plugin
        reply = client.globalcontroller.submit_pipeline(cadl)
        # name of pipeline remove when finished
        print('Status of filerepo pipeline submit: ' + str(reply))

        pipeline_id = reply['gpipeline_id']
        while client.globalcontroller.get_pipeline_status(pipeline_id) != 10:
            print('waiting for pipeline_id: ' + pipeline_id + ' to come online')
            time.sleep(2)

        # wait for sync
        for i in range(120):
            time.sleep(1)

        # remove the pipeline
        #client.globalcontroller.remove_pipeline(pipeline_id)

        #while client.globalcontroller.get_pipeline_status(pipeline_id) == 10:
        #    print('waiting for pipeline_id: ' + pipeline_id + ' to shutdown')
        #    time.sleep(1)

def filerepo_deploy_multi_node_tox_results(client, dst_region, dst_agent):

    #wait if client is not connected
    while not client.connected():
        print('Waiting on client connection')
        time.sleep(10)
        client.connect()

    if client.agents.is_controller_active(dst_region, dst_agent):

        # An optional custom logger callback
        def logger_callback(n):
            print("Custom logger callback Message = " + str(n))

        # Optionally connect to the agent logger stream
        log = client.get_logstreamer(logger_callback)
        log.connect()
        # Enable logging stream, this needs work, should be selectable via class and level
        log.update_config(dst_region, dst_agent)

        print('Global Controller Status: ' + str(client.agents.get_controller_status(dst_region, dst_agent)))

        #upload filerepo plugin to global controller
        jar_file_path = get_plugin_from_git("https://github.com/CrescoEdge/filerepo/releases/download/1.1-SNAPSHOT/filerepo-1.1-SNAPSHOT.jar")
        #jar_file_path = '/Users/cody/IdeaProjects/filerepo/target/filerepo-1.1-SNAPSHOT.jar'
        reply = client.globalcontroller.upload_plugin_global(jar_file_path)
        print("upload status: " + str(reply))
        print("plugin config: " + decompress_param(reply['configparams']))


        # create unique file repo name
        filerepo_name = str(uuid.uuid1())
        # location to sync
        #src_repo_path = 'test_data/' + str(uuid.uuid1())
        #src_repo_path = os.path.abspath(src_repo_path)
        #os.makedirs(src_repo_path)
        #print('src_repo_path: ' + src_repo_path)
        # location to store
        ##dst_repo_path = 'test_data/' + str(uuid.uuid1())
        #dst_repo_path = os.path.abspath(dst_repo_path)
        #os.makedirs(dst_repo_path)
        #print('dst_repo_path: ' + dst_repo_path)

        # create files to replicate
        #for i in range(20):
        #    Path(src_repo_path + '/' + str(i)).touch()

        # describe the dataplane query allowing python client to listen in on filerepo communications
        # this is not needed, but lets us see what is being communicated by the plugins
        stream_query = "filerepo_name='" + filerepo_name + "' AND broadcast"
        print('Client stream query ' + stream_query)
        # create a dataplane listener for incoming data

        # example of an (optional) custom callback to process incoming data from the dataframe
        def dp_callback(n):
            n = json.loads(n)
            print("Custom DP callback Message = " + str(n))
            print("Custom DP callback Message Type = " + str(type(n)))

        #print('Connecting to DP')
        #dp = client.get_dataplane(stream_query,dp_callback)
        # connect the listener
        #dp.connect()

        # node 0 : file repo sender configuration
        # Use base configparams (plugin_name, md5, etc.) that were extracted during plugin upload
        configparams = json.loads(decompress_param(reply['configparams']))

        cadl = dict()
        cadl['pipeline_id'] = '0'
        cadl['pipeline_name'] = str(uuid.uuid1())
        cadl['nodes'] = []
        cadl['edges'] = []

        params0 = dict()
        # Add plugin information
        params0['pluginname'] = configparams['pluginname']
        params0['md5'] = configparams['md5']
        params0['version'] = configparams['version']
        params0['persistence_code'] = '10'
        # Add location information
        params0["location_region"] = 'lab'
        params0["location_agent"] = 'MS4500'
        # Add repo name, which is used in the broadcast of state
        params0["filerepo_name"] = filerepo_name
        # Add scan_dir config telling filerepo to be a sender, and sync our local repo
        params0["scan_dir"] = 'f:\\2022\\PMDRUG'
        params0["scan_recursive"] = 'true'

        node0 = dict()
        node0['type'] = 'dummy'
        node0['node_name'] = 'SRC Plugin'
        node0['node_id'] = 0
        node0['isSource'] = False
        node0['workloadUtil'] = 0
        node0['params'] = params0

        params1 = dict()
        # Add plugin information
        params1['pluginname'] = configparams['pluginname']
        params1['md5'] = configparams['md5']
        params1['version'] = configparams['version']
        params0['persistence_code'] = '10'
        # Add location information
        params1["location_region"] = 'lab'
        params1["location_agent"] = 'controller'
        # Add repo name, which is used in the broadcast of state
        params1["filerepo_name"] = filerepo_name
        # Add repo_dir config telling filerepo to recv
        params1["repo_dir"] = '\\\\ukhcdata\\dept\\Laboratory Services\\Chandler Clinical Lab\\HLB CoreLabMT\\SPECIAL CHEMISTRY\\RawData\\MS4500\\RESULTS'

        node1 = dict()
        node1['type'] = 'dummy'
        node1['node_name'] = 'DST Plugin'
        node1['node_id'] = 1
        node1['isSource'] = False
        node1['workloadUtil'] = 0
        node1['params'] = params1

        edge0 = dict()
        edge0['edge_id'] = 0
        edge0['node_from'] = 0
        edge0['node_to'] = 1
        edge0['params'] = dict()

        cadl['nodes'].append(node0)
        cadl['nodes'].append(node1)
        cadl['edges'].append(edge0)


        # Push config and start sending repo plugin
        reply = client.globalcontroller.submit_pipeline(cadl)
        # name of pipeline remove when finished
        print('Status of filerepo pipeline submit: ' + str(reply))

        pipeline_id = reply['gpipeline_id']
        while client.globalcontroller.get_pipeline_status(pipeline_id) != 10:
            print('waiting for pipeline_id: ' + pipeline_id + ' to come online')
            time.sleep(2)

        # wait for sync
        for i in range(120):
            time.sleep(1)

        # remove the pipeline
        #client.globalcontroller.remove_pipeline(pipeline_id)

        #while client.globalcontroller.get_pipeline_status(pipeline_id) == 10:
        #    print('waiting for pipeline_id: ' + pipeline_id + ' to shutdown')
        #    time.sleep(1)


def filerepo_deploy_multi_node_rec(client, dst_region, dst_agent):

    #wait if client is not connected
    while not client.connected():
        print('Waiting on client connection')
        time.sleep(10)
        client.connect()

    if client.agents.is_controller_active(dst_region, dst_agent):

        # An optional custom logger callback
        #def logger_callback(n):
        #    print("Custom logger callback Message = " + str(n))

        # Optionally connect to the agent logger stream
        #log = client.get_logstreamer(logger_callback)
        #log.connect()
        # Enable logging stream, this needs work, should be selectable via class and level
        #log.update_config(dst_region, dst_agent)

        print('Global Controller Status: ' + str(client.agents.get_controller_status(dst_region, dst_agent)))

        #upload filerepo plugin to global controller
        #jar_file_path = get_plugin_from_git("https://github.com/CrescoEdge/filerepo/releases/download/1.1-SNAPSHOT/filerepo-1.1-SNAPSHOT.jar")
        jar_file_path = '/Users/cody/IdeaProjects/filerepo/target/filerepo-1.1-SNAPSHOT.jar'
        reply = client.globalcontroller.upload_plugin_global(jar_file_path)
        print("upload status: " + str(reply))
        print("plugin config: " + decompress_param(reply['configparams']))


        # create unique file repo name
        filerepo_name = str(uuid.uuid1())
        # location to sync
        #src_repo_path = 'test_data/' + str(uuid.uuid1())
        #src_repo_path = os.path.abspath(src_repo_path)
        #os.makedirs(src_repo_path)
        #print('src_repo_path: ' + src_repo_path)
        # location to store
        ##dst_repo_path = 'test_data/' + str(uuid.uuid1())
        #dst_repo_path = os.path.abspath(dst_repo_path)
        #os.makedirs(dst_repo_path)
        #print('dst_repo_path: ' + dst_repo_path)

        # create files to replicate
        #for i in range(20):
        #    Path(src_repo_path + '/' + str(i)).touch()

        # describe the dataplane query allowing python client to listen in on filerepo communications
        # this is not needed, but lets us see what is being communicated by the plugins
        stream_query = "filerepo_name='" + filerepo_name + "' AND broadcast"
        print('Client stream query ' + stream_query)
        # create a dataplane listener for incoming data

        # example of an (optional) custom callback to process incoming data from the dataframe
        def dp_callback(n):
            n = json.loads(n)
            print("Custom DP callback Message = " + str(n))
            print("Custom DP callback Message Type = " + str(type(n)))

        #print('Connecting to DP')
        #dp = client.get_dataplane(stream_query,dp_callback)
        # connect the listener
        #dp.connect()

        # node 0 : file repo sender configuration
        # Use base configparams (plugin_name, md5, etc.) that were extracted during plugin upload
        configparams = json.loads(decompress_param(reply['configparams']))

        cadl = dict()
        cadl['pipeline_id'] = '0'
        cadl['pipeline_name'] = str(uuid.uuid1())
        cadl['nodes'] = []
        cadl['edges'] = []

        params0 = dict()
        # Add plugin information
        params0['pluginname'] = configparams['pluginname']
        params0['md5'] = configparams['md5']
        params0['version'] = configparams['version']
        params0['persistence_code'] = '10'
        # Add location information
        params0["location_region"] = 'global-region'
        params0["location_agent"] = 'myagent'
        # Add repo name, which is used in the broadcast of state
        params0["filerepo_name"] = filerepo_name
        # Add scan_dir config telling filerepo to be a sender, and sync our local repo
        params0["scan_dir"] = '/Users/cody/Downloads/test_out'
        params0["scan_recursive"] = 'true'

        node0 = dict()
        node0['type'] = 'dummy'
        node0['node_name'] = 'SRC Plugin'
        node0['node_id'] = 0
        node0['isSource'] = False
        node0['workloadUtil'] = 0
        node0['params'] = params0

        params1 = dict()
        # Add plugin information
        params1['pluginname'] = configparams['pluginname']
        params1['md5'] = configparams['md5']
        params1['version'] = configparams['version']
        params0['persistence_code'] = '10'
        # Add location information
        params1["location_region"] = 'global-region'
        params1["location_agent"] = 'global-controller'
        # Add repo name, which is used in the broadcast of state
        params1["filerepo_name"] = filerepo_name
        # Add repo_dir config telling filerepo to recv
        params1["repo_dir"] = '/Users/cody/Downloads/test_in'

        node1 = dict()
        node1['type'] = 'dummy'
        node1['node_name'] = 'DST Plugin'
        node1['node_id'] = 1
        node1['isSource'] = False
        node1['workloadUtil'] = 0
        node1['params'] = params1

        edge0 = dict()
        edge0['edge_id'] = 0
        edge0['node_from'] = 0
        edge0['node_to'] = 1
        edge0['params'] = dict()

        cadl['nodes'].append(node0)
        cadl['nodes'].append(node1)
        cadl['edges'].append(edge0)


        # Push config and start sending repo plugin
        reply = client.globalcontroller.submit_pipeline(cadl)
        # name of pipeline remove when finished
        print('Status of filerepo pipeline submit: ' + str(reply))

        pipeline_id = reply['gpipeline_id']
        while client.globalcontroller.get_pipeline_status(pipeline_id) != 10:
            print('waiting for pipeline_id: ' + pipeline_id + ' to come online')
            time.sleep(2)

        # wait for sync
        #for i in range(120):
        #    time.sleep(1)

        # remove the pipeline
        #client.globalcontroller.remove_pipeline(pipeline_id)

        #while client.globalcontroller.get_pipeline_status(pipeline_id) == 10:
        #    print('waiting for pipeline_id: ' + pipeline_id + ' to shutdown')
        #    time.sleep(1)

def listen_dp(client, ident_key,ident_id):

    config_dp = dict()
    config_dp['ident_key'] = ident_key
    config_dp['ident_id'] = ident_id
    # config_dp['stream_query'] = ident_key + "='" + ident_id + "' and type='" + "input" + "'"
    config_dp['io_type_key'] = 'type'
    config_dp['output_id'] = 'output'
    config_dp['input_id'] = 'output'

    json_config = json.dumps(config_dp)
    print(json_config)

    # create a dataplane listener for incoming data

    # example of an (optional) custom callback to write executor output to a file
    def dp_callback(n):
        print("Custom DP callback Message = " + str(n))

    print('Connecting to DP')
    dp = client.get_dataplane(json_config, dp_callback)
    # connect the listener
    dp.connect()

    # wait for sync
    while True:
        #dp.send("WTF")
        time.sleep(5)


def debug_agent(client, dst_region, dst_agent):

    #wait if client is not connected
    while not client.connected():
        print('Waiting on client connection')
        time.sleep(10)
        client.connect()

    if client.agents.is_controller_active(dst_region, dst_agent):
        # An optional custom logger callback
        def logger_callback(n):
            print("Custom logger callback Message = " + str(n))

        # Optionally connect to the agent logger stream
        log = client.get_logstreamer(logger_callback)
        log.connect()
        # Enable logging stream, this needs work, should be selectable via class and level
        #log.update_config(dst_region, dst_agent)
        log.update_config_class(dst_region, dst_agent, 'Trace', 'org.apache.activemq')
        log.update_config_class(dst_region, dst_agent, 'Trace', 'org.apache.activemq.*')
        log.update_config_class(dst_region, dst_agent, 'Trace', 'org.apache.activemq.spring')
        log.update_config_class(dst_region, dst_agent, 'Trace', 'org.apache.activemq.broker')


        ident_key = 'stream_name'
        ident_id = '1234'

        config_dp = dict()
        config_dp['ident_key'] = ident_key
        config_dp['ident_id'] = ident_id
        #config_dp['stream_query'] = ident_key + "='" + ident_id + "' and type='" + "input" + "'"
        config_dp['io_type_key'] = 'type'
        config_dp['output_id'] = 'output'
        config_dp['input_id'] = 'output'

        json_config = json.dumps(config_dp)
        print(json_config)
        # create a dataplane listener for incoming data

        # example of an (optional) custom callback to write executor output to a file
        def dp_callback(n):

            print("Custom DP callback Message = " + str(n))

        print('Connecting to DP')
        dp = client.get_dataplane(json_config, dp_callback)
        # connect the listener
        dp.connect()


        # wait for sync
        while True:
            #dp.send("WTF")
            time.sleep(1)

def get_dp_log(client, ident_key, ident_id):

    # wait if client is not connected
    while not client.connected():
        print('Waiting on client connection')
        time.sleep(10)
        client.connect()

    config_dp = dict()
    config_dp['ident_key'] = ident_key
    config_dp['ident_id'] = ident_id
    # config_dp['stream_query'] = ident_key + "='" + ident_id + "' and type='" + "input" + "'"
    config_dp['io_type_key'] = 'type'
    config_dp['output_id'] = 'output'
    config_dp['input_id'] = 'output'

    json_config = json.dumps(config_dp)
    print(json_config)

    # create a dataplane listener for incoming data

    # example of an (optional) custom callback to write executor output to a file
    def dp_callback(n):
        print("Custom DP callback Message = " + str(n))

    print('Connecting to DP')
    dp = client.get_dataplane(json_config, dp_callback)
    # connect the listener
    dp.connect()

    while True:
        time.sleep(1)

def filerepo_deploy_single_node(client, dst_region, dst_agent):

    #wait if client is not connected
    while not client.connected():
        print('Waiting on client connection')
        time.sleep(10)
        client.connect()

    if client.agents.is_controller_active(dst_region, dst_agent):

        # An optional custom logger callback
        def logger_callback(n):
            print("Custom logger callback Message = " + str(n))

        # Optionally connect to the agent logger stream
        log = client.get_logstreamer(logger_callback)
        log.connect()
        # Enable logging stream, this needs work, should be selectable via class and level
        log.update_config(dst_region, dst_agent)

        print('Global Controller Status: ' + str(client.agents.get_controller_status(dst_region, dst_agent)))

        #upload filerepo plugin to global controller
        jar_file_path = get_plugin_from_git("https://github.com/CrescoEdge/filerepo/releases/download/1.1-SNAPSHOT/filerepo-1.1-SNAPSHOT.jar")
        reply = client.globalcontroller.upload_plugin_global(jar_file_path)
        print("upload status: " + str(reply))
        print("plugin config: " + decompress_param(reply['configparams']))


        # create unique file repo name
        filerepo_name = str(uuid.uuid1())
        # location to sync
        src_repo_path = 'test_data/' + str(uuid.uuid1())
        src_repo_path = os.path.abspath(src_repo_path)
        os.makedirs(src_repo_path)
        print('src_repo_path: ' + src_repo_path)
        # location to store
        dst_repo_path = 'test_data/' + str(uuid.uuid1())
        dst_repo_path = os.path.abspath(dst_repo_path)
        os.makedirs(dst_repo_path)
        print('dst_repo_path: ' + dst_repo_path)

        # create files to replicate
        for i in range(20):
            Path(src_repo_path + '/' + str(i)).touch()

        # describe the dataplane query allowing python client to listen in on filerepo communications
        # this is not needed, but lets us see what is being communicated by the plugins
        stream_query = "filerepo_name='" + filerepo_name + "' AND broadcast"
        print('Client stream query ' + stream_query)
        # create a dataplane listener for incoming data

        # example of an (optional) custom callback to process incoming data from the dataframe
        def dp_callback(n):
            n = json.loads(n)
            print("Custom DP callback Message = " + str(n))
            print("Custom DP callback Message Type = " + str(type(n)))

        print('Connecting to DP')
        dp = client.get_dataplane(stream_query,dp_callback)
        # connect the listener
        dp.connect()

        # node 0 : file repo sender configuration
        # Use base configparams (plugin_name, md5, etc.) that were extracted during plugin upload
        configparams = json.loads(decompress_param(reply['configparams']))

        cadl = dict()
        cadl['pipeline_id'] = '0'
        cadl['pipeline_name'] = str(uuid.uuid1())
        cadl['nodes'] = []
        cadl['edges'] = []

        params0 = dict()
        # Add plugin information
        params0['pluginname'] = configparams['pluginname']
        params0['md5'] = configparams['md5']
        params0['version'] = configparams['version']
        # Add location information
        params0["location_region"] = dst_region
        params0["location_agent"] = dst_agent
        # Add repo name, which is used in the broadcast of state
        params0["filerepo_name"] = filerepo_name
        # Add scan_dir config telling filerepo to be a sender, and sync our local repo
        params0["scan_dir"] = src_repo_path

        node0 = dict()
        node0['type'] = 'dummy'
        node0['node_name'] = 'SRC Plugin'
        node0['node_id'] = 0
        node0['isSource'] = False
        node0['workloadUtil'] = 0
        node0['params'] = params0

        params1 = dict()
        # Add plugin information
        params1['pluginname'] = configparams['pluginname']
        params1['md5'] = configparams['md5']
        params1['version'] = configparams['version']
        # Add location information
        params1["location_region"] = dst_region
        params1["location_agent"] = dst_agent
        # Add repo name, which is used in the broadcast of state
        params1["filerepo_name"] = filerepo_name
        # Add repo_dir config telling filerepo to recv
        params1["repo_dir"] = dst_repo_path

        node1 = dict()
        node1['type'] = 'dummy'
        node1['node_name'] = 'DST Plugin'
        node1['node_id'] = 1
        node1['isSource'] = False
        node1['workloadUtil'] = 0
        node1['params'] = params1

        edge0 = dict()
        edge0['edge_id'] = 0
        edge0['node_from'] = 0
        edge0['node_to'] = 1
        edge0['params'] = dict()

        cadl['nodes'].append(node0)
        cadl['nodes'].append(node1)
        cadl['edges'].append(edge0)


        # Push config and start sending repo plugin
        reply = client.globalcontroller.submit_pipeline(cadl)
        # name of pipeline remove when finished
        print('Status of filerepo pipeline submit: ' + str(reply))

        pipeline_id = reply['gpipeline_id']
        while client.globalcontroller.get_pipeline_status(pipeline_id) != 10:
            print('waiting for pipeline_id: ' + pipeline_id + ' to come online')
            time.sleep(2)



        # wait for sync
        for i in range(20):
            time.sleep(1)

        # remove the pipeline
        client.globalcontroller.remove_pipeline(pipeline_id)

        while client.globalcontroller.get_pipeline_status(pipeline_id) == 10:
            print('waiting for pipeline_id: ' + pipeline_id + ' to shutdown')
            time.sleep(1)

def aiapi_deploy_single_node(client, dst_region, dst_agent):

    #wait if client is not connected
    while not client.connected():
        print('Waiting on client connection')
        time.sleep(10)
        client.connect()

    if client.agents.is_controller_active(dst_region, dst_agent):

        print('Global Controller Status: ' + str(client.agents.get_controller_status(dst_region, dst_agent)))

        location = 'WS-9MQ8PR3'
        llm_region = None
        llm_agent = None

        for agent_info in client.globalcontroller.get_agent_list():
            if agent_info['location'] == location:
                llm_region = agent_info['region']
                llm_agent = agent_info['name']

        pipeline_id = 'resource-377a54e8-14cf-4ff7-b040-afef73f879dd'

        if pipeline_id is None:

            #pipeline_name = str(uuid.uuid1())
            pipeline_name = "LLM FUN"
            #upload filerepo plugin to global controller
            jar_file_path = '/Users/cody/IdeaProjects/aiapi/target/aiapi-1.1-SNAPSHOT.jar'
            #jar_file_path = get_plugin_from_git("https://github.com/CrescoEdge/filerepo/releases/download/1.1-SNAPSHOT/filerepo-1.1-SNAPSHOT.jar")

            reply = client.globalcontroller.upload_plugin_global(jar_file_path)
            print("upload status: " + str(reply))
            print("plugin config: " + decompress_param(reply['configparams']))

            # node 0 : file repo sender configuration
            # Use base configparams (plugin_name, md5, etc.) that were extracted during plugin upload
            configparams = json.loads(decompress_param(reply['configparams']))

            cadl = dict()
            cadl['pipeline_id'] = '0'
            cadl['pipeline_name'] = pipeline_name
            cadl['nodes'] = []
            cadl['edges'] = []

            params0 = dict()
            # Add plugin information
            params0['pluginname'] = configparams['pluginname']
            params0['md5'] = configparams['md5']
            params0['version'] = configparams['version']
            # Add location information
            params0["location_region"] = llm_region
            params0["location_agent"] = llm_agent

            node0 = dict()
            node0['type'] = 'dummy'
            node0['node_name'] = 'SRC Plugin'
            node0['node_id'] = 0
            node0['isSource'] = False
            node0['workloadUtil'] = 0
            node0['params'] = params0

            cadl['nodes'].append(node0)


            # Push config and start executor plugin
            reply = client.globalcontroller.submit_pipeline(cadl)
            # name of pipeline remove when finished
            print('Status of executor pipeline submit: ' + str(reply))

            pipeline_id = reply['gpipeline_id']
            while client.globalcontroller.get_pipeline_status(pipeline_id) != 10:
                print('waiting for pipeline_id: ' + pipeline_id + ' to come online')
                time.sleep(2)

            #get the plugin_id of the executor plugin
            executor_plugin_id = client.globalcontroller.get_pipeline_info(pipeline_id)['nodes'][0]['node_id']
            print('pipeline_id:', pipeline_id)
        else:
            print(client.globalcontroller.get_pipeline_list())
            llm_plugin = client.globalcontroller.get_pipeline_info(pipeline_id)['nodes'][0]['node_id']
            #client.globalcontroller.remove_pipeline(pipeline_id)


        # this code makes use of a global message to find a specific plugin type, then send a message to that plugin
        # send a config message to setup the config of the executor
        message_event_type = 'EXEC'
        message_payload = dict()
        message_payload['action'] = 'getllm'
        message_payload['endpoint_url'] = 'http://10.32.33.107:8080/generate'
        #message_payload['endpoint_url'] = 'http://127.0.0.1:8080/generate'
        message_payload['input_text'] = 'Natalia sold clips to 48 of her friends in April, and then she sold half as many clips in May. How many clips did Natalia sell altogether in April and May?'
        message_payload['max_tokens'] = '500'

        print('MESSAGE OUT:')
        print('llm_region:', llm_region, 'llm_agent:', llm_agent, 'llm_plugin:', llm_plugin)
        result = client.messaging.global_plugin_msgevent(True, message_event_type, message_payload, llm_region, llm_agent, llm_plugin)
        print('DO IT:')
        print(result)

        exit()

        # remove the pipeline
        client.globalcontroller.remove_pipeline(pipeline_id)

        while client.globalcontroller.get_pipeline_status(pipeline_id) == 10:
            print('waiting for pipeline_id: ' + pipeline_id + ' to shutdown')
            time.sleep(1)


def upgrade_controller_plugin(client, dst_region, dst_agent, jar_file_path):

    print('updating agent: region=' + dst_region + ' agent=' + dst_agent)

    #wait if client is not connected
    while not client.connected():
        print('Waiting on client connection')
        time.sleep(10)
        client.connect()

    print('post connect')
    # An optional custom logger callback
    def logger_callback(n):
        print("Custom logger callback Message = " + str(n))

    # Optionally connect to the agent logger stream
    log = client.get_logstreamer(logger_callback)
    log.connect()
    # Enable logging stream, this needs work, should be selectable via class and level
    log.update_config(dst_region, dst_agent)

    #print('Agent Status: ' + str(client.agents.get_controller_status(dst_region, dst_agent)))

    #if client.agents.is_controller_active(dst_region, dst_agent):
    if True:
        print('Agent Controller is Active Uploading')
        # reply = client.globalcontroller.upload_plugin_global(jar_file_path)
        reply = client.agents.upload_plugin_agent(dst_region, dst_agent, jar_file_path)
        print("upload" + str(reply))
        if reply['is_updated']:
            remote_jar_file_path = reply['jar_file_path']
            print(remote_jar_file_path)
            print('updating agent with local jar ' + remote_jar_file_path)
            client.agents.update_plugin_agent(dst_region, dst_agent, remote_jar_file_path)
        # print("configparams: " + decompress_param(reply['configparams']))
        # reply = client.agents.repo_pull_plugin_agent(dst_region, dst_agent, jar_file_path)
        # print("config: " + decompress_param(reply['configparams']))
        # client.agents.update_plugin_agent(dst_region, dst_agent, jar_file_path)

def remove_dead_plugins(client, dst_region, dst_agent):

    #wait if client is not connected
    while not client.connected():
        print('Waiting on client connection')
        time.sleep(10)
        client.connect()

    #client.admin.restartcontroller(dst_region,dst_agent)

# An optional custom logger callback
    def logger_callback(n):
        print("Custom logger callback Message = " + str(n))

        # Optionally connect to the agent logger stream
    log = client.get_logstreamer(logger_callback)
    log.connect()
        # Enable logging stream, this needs work, should be selectable via class and level
    log.update_config(dst_region, 'controller')
    #log.update_config(dst_region, dst_agent)

    time.sleep(10)

    client.admin.restartcontroller(dst_region,dst_agent)


    reply = client.agents.list_plugin_agent(dst_region, dst_agent)

    for plugin in reply:
        print(plugin)
            # if(plugin['pluginname'] == 'io.cresco.executor'):
            #    print(plugin)
            # responce = client.agents.remove_plugin_agent(dst_region, dst_agent, plugin['plugin_id'])
            # print(responce)

    agents = client.globalcontroller.get_agent_list(dst_region)

    for agent in agents:
        print(agent)

    while True:
        time.sleep(1)


def remove_dead_plugins2(client, dst_region, dst_agent):

    #wait if client is not connected
    while not client.connected():
        print('Waiting on client connection')
        time.sleep(10)
        client.connect()

    #client.admin.restartcontroller(dst_region,dst_agent)

    if client.agents.is_controller_active(dst_region, dst_agent):

        # An optional custom logger callback
        def logger_callback(n):
            print("Custom logger callback Message = " + str(n))

        # Optionally connect to the agent logger stream
        #log = client.get_logstreamer(logger_callback)
        #log.connect()
        # Enable logging stream, this needs work, should be selectable via class and level
        #log.update_config(dst_region, dst_agent)

        agents = client.globalcontroller.get_agent_list(dst_region)
        print(agents)
        for agent in agents:
            print(agent['name'])
            reply = client.agents.list_plugin_agent(dst_region, agent['name'])
            for plugin in reply:
                # print("what")
                print(plugin)
                if(plugin['pluginname'] == 'io.cresco.filerepo'):
                #if (plugin['pluginname'] == 'io.cresco.executor'):
                    print(plugin)
                    responce = client.agents.remove_plugin_agent(dst_region, dst_agent, plugin['plugin_id'])
                    print(responce)

        #time.sleep(300)

#old

def get_repo_plugin(pluginslist):
    plugin_name = 'io.cresco.repo'
    pluginlist = pluginslist['plugins']
    for plugin in pluginlist:
        if plugin['pluginname'] == plugin_name:
            return plugin

def submit_app(client, jar_info):

    cadl = dict()
    cadl['pipeline_id'] = '0'
    cadl['pipeline_name'] = 'mycadl'
    cadl['nodes'] = []
    cadl['edges'] = []

    params0 = dict()
    params0['pluginname'] = jar_info['pluginname']
    params0['md5'] = jar_info['md5']
    params0['jarfile'] = jar_info['jarfile']
    params0['version'] = jar_info['version']
    params0['mode'] = 0
    params0["location_region"] = "global-region"
    params0["location_agent"] = "global-controller"

    node0 = dict()
    node0['type'] = 'dummy'
    node0['node_name'] = 'Plugin 0'
    node0['node_id'] = 0
    node0['isSource'] = False
    node0['workloadUtil'] = 0
    node0['params'] = params0

    params1 = dict()
    params1['pluginname'] = jar_info['pluginname']
    params1['md5'] = jar_info['md5']
    params1['jarfile'] = jar_info['jarfile']
    params1['version'] = jar_info['version']
    params1['mode'] = 1
    params1["location_region"] = "global-region"
    params1["location_agent"] = "global-controller"

    node1 = dict()
    node1['type'] = 'dummy'
    node1['node_name'] = 'Plugin 0'
    node1['node_id'] = 1
    node1['isSource'] = False
    node1['workloadUtil'] = 0
    node1['params'] = params1

    edge0 = dict()
    edge0['edge_id'] = 0
    edge0['node_from'] = 0
    edge0['node_to'] = 1
    edge0['params'] = dict()

    cadl['nodes'].append(node0)
    cadl['nodes'].append(node1)
    cadl['edges'].append(edge0)

    print(json.dumps(cadl, indent=4))

    message_event_type = 'CONFIG'
    message_payload = dict()
    message_payload['action'] = 'gpipelinesubmit'
    message_payload['action_gpipeline'] = compress_param(json.dumps(cadl))
    message_payload['action_tenantid'] = '0'

    print(type(client.messaging))
    retry = client.messaging.global_controller_msgevent(True, message_event_type, message_payload)
    #returns status and gpipeline_id
    return retry

def submit_lorawan_app(client, jar_info):

    cadl = dict()
    cadl['pipeline_id'] = '0'
    cadl['pipeline_name'] = str(uuid.uuid1())
    cadl['nodes'] = []
    cadl['edges'] = []

    num_nodes = 20
    metrics = ['co2','radon', 'rad']
    for i in range(num_nodes):
        metric = random.choice(metrics)

        params0 = dict()
        params0['pluginname'] = jar_info['pluginname']
        params0['md5'] = jar_info['md5']
        params0['jarfile'] = jar_info['md5']
        params0['version'] = jar_info['version']
        params0["location_region"] = "global-region"
        params0["location_agent"] = "global-controller"
        params0['source_name'] = metric + '_source'
        params0['urn'] = str(uuid.uuid1())
        params0['metric_name'] = metric
        params0['input_stream_name'] = jar_info['input_stream_name']

        node0 = dict()
        node0['type'] = metric
        node0['node_name'] = 'Metric ' + metric + ' producer'
        node0['node_id'] = 0
        node0['isSource'] = True
        node0['workloadUtil'] = 0
        node0['params'] = params0
        cadl['nodes'].append(node0)

    edge0 = dict()
    cadl['edges'].append(edge0)

    print(json.dumps(cadl, indent=4))

    message_event_type = 'CONFIG'
    message_payload = dict()
    message_payload['action'] = 'gpipelinesubmit'
    message_payload['action_gpipeline'] = compress_param(json.dumps(cadl))
    message_payload['action_tenantid'] = '0'

    reply = client.messaging.global_controller_msgevent(True, message_event_type, message_payload)

    pipeline_id = reply['gpipeline_id']
    while client.globalcontroller.get_pipeline_status(pipeline_id) != 10:
        print('waiting for pipeline_id: ' + pipeline_id + ' to come online' )
        time.sleep(1)
    #returns status and gpipeline_id
    return reply

def launch_apps(client, count):

    jar_file_path = 'cepdemo-1.0-SNAPSHOT.jar'
    jar_info = client.add_repo_plugin(jar_file_path)

    for i in range(count):
        submit_app(client, jar_info)
        time.sleep(1)

def shutdown_apps(client):
    message_event_type = 'EXEC'
    message_payload = dict()
    message_payload['action'] = 'getgpipelinestatus'

    retry = client.messaging.global_controller_msgevent(True, message_event_type, message_payload)
    pipelineinfo = json.loads(decompress_param(retry['pipelineinfo']))
    for pipeline in pipelineinfo['pipelines']:
        print(pipeline['pipeline_id'])
        message_event_type = 'CONFIG'
        message_payload = dict()
        message_payload['action'] = 'gpipelineremove'
        message_payload['action_pipelineid'] = pipeline['pipeline_id']
        retry = client.messaging.global_controller_msgevent(True, message_event_type, message_payload)
        print(retry)

def launch_single_lorawan(client):

    reply = client.agents.get_agent_list()[0]
    dst_region = reply['region']
    dst_agent = reply['name']

    jar_file_path = 'lorawandg-1.1-SNAPSHOT.jar'
    reply = client.plugin.upload_plugin_global(jar_file_path)
    print("upload" + str(reply))
    print("config: " + decompress_param(reply['configparams']))
    configparams = json.loads(decompress_param(reply['configparams']))
    stream_id = str(uuid.uuid1())
    configparams['input_stream_name'] = stream_id

    reply = client.plugin.add_plugin_agent(dst_region, dst_agent, configparams, None)
    plugin_id = reply['pluginid']

    dp = client.get_dataplane(stream_id)
    dp.connect()

    for i in range(25):
        time.sleep(1)

    dp.close()
    client.plugin.remove_plugin_agent(dst_region, dst_agent, plugin_id)

def create_cep(client, input_stream, output_stream, dst_region, dst_agent):

    input_stream_desc = "source string, urn string, metric string, ts long, value double";
    output_stream_desc = "source string, avgValue double"
    query = "from " + input_stream + "#window.timeBatch(5 sec) " \
                                     "select source, avg(value) as avgValue " \
                                     "  group by source " \
                                     "insert into " + output_stream + "; "

    client.agents.cepadd(input_stream, input_stream_desc, output_stream, output_stream_desc, query, dst_region, dst_agent)

def lorawan_reboot_loop(client):

    dst_region = "global-region"
    dst_agent = "global-controller"

    while (True):
        while not client.connected():
            time.sleep(1)
            client.connect()

        #client.admin.stopcontroller(dst_region, dst_agent)
        #exit(0)

        if client.agents.is_controller_active(dst_region, dst_agent):

            log = client.get_logstreamer()
            log.connect()
            log.update_config()

            print('controller is active: ' + str(client.agents.get_controller_status(dst_region, dst_agent)))
            jar_file_path = 'lorawandg-1.1-SNAPSHOT.jar'
            reply = client.globalcontroller.upload_plugin_global(jar_file_path)
            print("upload" + str(reply))
            print("config: " + decompress_param(reply['configparams']))
            configparams = json.loads(decompress_param(reply['configparams']))
            configparams['source_name'] = 'cody_source'
            configparams['urn'] = 'someurn'
            configparams['metric_name'] = 'radon'
            input_stream_id = 'inode' + str(uuid.uuid1()).replace('-', '')
            configparams['input_stream_name'] = input_stream_id
            reply = submit_lorawan_app(client, configparams)

            output_stream_id = 'inode' + str(uuid.uuid1()).replace('-', '')
            reply = create_cep(client, input_stream_id, output_stream_id, dst_region, dst_agent)

            stream_query = "stream_name='" + output_stream_id + "'"
            print(stream_query)
            dp = client.get_dataplane(stream_query)
            dp.connect()

            for i in range(15):
                time.sleep(1)

            dp.close()
            shutdown_apps(client)

            print('waiting for apps shutdown')
            while len(client.globalcontroller.get_pipeline_list()) != 0:
                time.sleep(5)

            print('controller shutdown restarting')
            client.admin.restartcontroller(dst_region, dst_agent)

            # kill entire jvm
            # client.admin.killjvm(dst_region, dst_agent)

            isRunning = True
            while isRunning:
                try:
                    print('controller status: ' + str(client.agents.get_controller_status(dst_region, dst_agent)))
                    # time.sleep(1)
                except:
                    isRunning = False

            time.sleep(5)
        else:
            print('controller is not active')
            time.sleep(5)

def filerepo_reboot_loop(client):

    dst_region = "global-region"
    dst_agent = "global-controller"

    while not client.connected():
        time.sleep(1)
        client.connect()

    if client.agents.is_controller_active(dst_region, dst_agent):
        #log = client.get_logstreamer()
        #log.connect()
        #log.update_config()

        '''
        scanDirString =  plugin.getConfig().getStringParam("scan_dir");
        fileRepoName =  plugin.getConfig().getStringParam("filerepo_name");
        /Users/cody/IdeaProjects/filerepo/t
        '''

        print('controller is active: ' + str(client.agents.get_controller_status(dst_region, dst_agent)))
        jar_file_path = 'filerepo-1.1-SNAPSHOT.jar'
        reply = client.globalcontroller.upload_plugin_global(jar_file_path)
        print("upload" + str(reply))
        print("config: " + decompress_param(reply['configparams']))
        configparams = json.loads(decompress_param(reply['configparams']))

        filerepo_name = 'demac'
        configparams['scan_dir'] = '/Users/cody/IdeaProjects/filerepo/t'
        configparams['filerepo_name'] = filerepo_name

        stream_query = "filerepo_name='" + filerepo_name + "' AND broadcast"
        print(stream_query)
        dp = client.get_dataplane(stream_query)
        dp.connect()

        #reply = launch_single_filerepo(client, configparams, dst_region, dst_agent)
        #print(reply)

        '''
        for i in range(10):
            time.sleep(1)

        plugin_id = reply['pluginid']
        reply = client.agents.remove_plugin_agent(dst_region,dst_agent,plugin_id)
        print(reply)
        '''

        configparams.pop('scan_dir', None)
        configparams['repo_dir'] = '/Users/cody/IdeaProjects/filerepo/rp0'
        #reply = launch_single_filerepo(client, configparams, dst_region, 'agent-controller')
        #print(reply)
        '''
        configparams['repo_dir'] = '/Users/cody/IdeaProjects/filerepo/rp1'
        reply = launch_single_filerepo(client, configparams, dst_region, dst_agent)
        print(reply)
        configparams['repo_dir'] = '/Users/cody/IdeaProjects/filerepo/rp2'
        reply = launch_single_filerepo(client, configparams, dst_region, dst_agent)
        print(reply)
        '''


        for i in range(120):
            time.sleep(1)

        #log.close()

def filerepo_deploy_lab(client):


    controller_dst_region = 'lab'
    controller_dst_agent = 'controller'
    ms_dst_region = 'lab'
    ms_dst_agent = 'ms4500'

    while not client.connected():
        time.sleep(1)
        client.connect()

    if client.agents.is_controller_active(controller_dst_region, controller_dst_agent):

        print('controller is active: ' + str(client.agents.get_controller_status(controller_dst_region, controller_dst_agent)))
        jar_file_path = 'filerepo-1.1-SNAPSHOT.jar'
        reply = client.globalcontroller.upload_plugin_global(jar_file_path)
        print("upload" + str(reply))
        print("config: " + decompress_param(reply['configparams']))
        controller_configparams = json.loads(decompress_param(reply['configparams']))

        filerepo_name = 'wiff'
        controller_configparams['scan_dir'] = 'DIRECTORY SENDING FROM'
        controller_configparams['filerepo_name'] = filerepo_name

        stream_query = "filerepo_name='" + filerepo_name + "' AND broadcast"
        print(stream_query)
        dp = client.get_dataplane(stream_query)
        dp.connect()

        #reply = launch_single_filerepo(client, controller_configparams, controller_dst_region, controller_dst_agent)
        #print(reply)


        ms_configparams = json.loads(decompress_param(reply['configparams']))
        ms_configparams['filerepo_name'] = filerepo_name
        ms_configparams['repo_dir'] = 'DIRECTORY_SENDING_TO' \

        #reply = launch_single_filerepo(client, ms_configparams, ms_dst_region, ms_dst_agent)
        #print(reply)

        time.sleep(60)

