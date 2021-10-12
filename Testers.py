import json
import random
import time
import uuid
import os
import urllib.request

from pycrescolib.utils import compress_param, decompress_param
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

        #log = client.get_logstreamer()
        #log.connect()
        #log.update_config()

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
        os.makedirs(src_repo_path)
        print('src_repo_path: ' + src_repo_path)
        # location to store
        dst_repo_path = 'test_data/' + str(uuid.uuid1())
        os.makedirs(dst_repo_path)
        print('dst_repo_path: ' + dst_repo_path)

        # create files to replicate
        for i in range(20):
            Path(src_repo_path + '/' + str(i)).touch()

        # describe the dataplane query allowing python client to listen in on filerepo communications
        stream_query = "filerepo_name='" + filerepo_name + "' AND broadcast"
        print('Client stream query ' + stream_query)
        # create a dataplane listner for incoming data
        print('* Data plane is currently broken on the client*')
        #dp = client.get_dataplane(stream_query)
        # connect the listener
        #dp.connect()

        # node 0 : file repo sender configuration
        # Use base configparams (plugin_name, md5, etc.) that were extracted during plugin upload
        configparams = json.loads(decompress_param(reply['configparams']))
        # Add repo name, which is used in the broadcast of state
        configparams['filerepo_name'] = filerepo_name
        # Add scan_dir config telling filerepo to be a sender, and sync our local repo
        configparams['scan_dir'] = src_repo_path

        # Push config and start sending repo plugin
        reply = client.agents.add_plugin_agent(dst_region, dst_agent, configparams, None)
        # name of src plugin to remove when finished
        src_repo_plugin_id = reply['pluginid']

        print('Status of filerepo sender submit: ' + str(reply))

        # Take existing config and modify it for the recv plugin
        # Remove the scan_dir config, so sender functions don't start
        configparams.pop('scan_dir', None)
        # Add repo_dir location
        configparams['repo_dir'] = dst_repo_path

        # Push config and start recv repo plugin
        reply = client.agents.add_plugin_agent(dst_region, dst_agent, configparams, None)
        # name of dst plugin to remove when finished
        dst_repo_plugin_id = reply['pluginid']
        print('Status of filerepo recv submit: ' + str(reply))

        # wait for 2 min
        for i in range(60):
            time.sleep(1)

        # remove recv plugin
        reply = client.agents.remove_plugin_agent(dst_region, dst_agent, dst_repo_plugin_id)
        print('Status of filerepo recv remove: ' + str(reply))

        # remove send plugin
        reply = client.agents.remove_plugin_agent(dst_region, dst_agent, src_repo_plugin_id)
        print('Status of filerepo src remove: ' + str(reply))

        #close dp
        #dp.close()





#old
def upgrade_controller_plugin(client, dst_region, dst_agent, jar_file_path):

    #reply = client.globalcontroller.upload_plugin_global(jar_file_path)
    reply = client.agents.upload_plugin_agent(dst_region,dst_agent,jar_file_path)
    print("upload" + str(reply))
    if reply['is_updated']:
        remote_jar_file_path = reply['jar_file_path']
        print(remote_jar_file_path)
        print('updating agent with local jar ' + remote_jar_file_path)
        client.agents.update_plugin_agent(dst_region, dst_agent, remote_jar_file_path)
    #print("configparams: " + decompress_param(reply['configparams']))
    #reply = client.agents.repo_pull_plugin_agent(dst_region, dst_agent, jar_file_path)
    #print("config: " + decompress_param(reply['configparams']))
    #client.agents.update_plugin_agent(dst_region, dst_agent, jar_file_path)

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

        reply = launch_single_filerepo(client, configparams, dst_region, dst_agent)
        print(reply)

        '''
        for i in range(10):
            time.sleep(1)

        plugin_id = reply['pluginid']
        reply = client.agents.remove_plugin_agent(dst_region,dst_agent,plugin_id)
        print(reply)
        '''

        configparams.pop('scan_dir', None)
        configparams['repo_dir'] = '/Users/cody/IdeaProjects/filerepo/rp0'
        reply = launch_single_filerepo(client, configparams, dst_region, 'agent-controller')
        print(reply)
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

