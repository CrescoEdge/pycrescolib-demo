
from pycrescolib.clientlib import clientlib

from Testers import filerepo_deploy_single_node, filerepo_deploy_multi_node, debug_agent, \
    executor_deploy_single_node_pipeline, executor_deploy_single_node_plugin

if __name__ == "__main__":

    #Hostname of the agent global controler hosting the wsapi plugin
    host = 'localhost'
    #host = '10.28.71.118'
    #Port of wsapi / Default: 8282
    port = 8282
    #Service key for wsapu instance
    service_key = '1234'

    # init pycrescolib client
    client = clientlib(host, port, service_key)

    #connect client to wsapi plugin
    if client.connect():

        #test_case = 0 # Get a list of agents from a controller
        #test_case = 1 # Filerepo example on a single node
        test_case = 5 # Executor example on a single node

        #test_case 0: Get the list of agents from the agent global controller
        if test_case == 0:

            #name of agent global controller region
            dst_region = 'global-region'
            #name of agent global controller agent
            dst_agent = 'global-controller'

            #Print status of the global controller
            print('Global Controller Status: ' + str(client.agents.get_controller_status(dst_region, dst_agent)))
            #If the controller is active continue communication
            if client.agents.is_controller_active(dst_region, dst_agent):
                #Get agent list in json form
                reply = client.globalcontroller.get_agent_list()
                #Print agent list
                print('Agent list: ' + str(reply))


        if test_case == 1:

            # name of agent global controller region
            dst_region = 'global-region'
            # name of agent global controller agent
            dst_agent = 'global-controller'

            filerepo_deploy_single_node(client, dst_region, dst_agent)

        if test_case == 2:

            # name of agent global controller region
            dst_region = 'global-region'
            # name of agent global controller agent
            dst_agent = 'global-controller'

            executor_deploy_single_node_pipeline(client, dst_region, dst_agent)

        if test_case == 3:

            # name of agent global controller region
            dst_region = 'lab'
            # name of agent global controller agent
            dst_agent = 'controller'

            filerepo_deploy_multi_node(client, dst_region, dst_agent)

        if test_case == 4:

            # name of agent global controller region
            dst_region = 'lab'
            # name of agent global controller agent
            dst_agent = 'controller'

            debug_agent(client, dst_region, dst_agent)


        if test_case == 5:

            # name of agent global controller region
            dst_region = 'global-region'
            # name of agent global controller agent
            dst_agent = 'global-controller'

            executor_deploy_single_node_plugin(client, dst_region, dst_agent)


        client.close()



        #dst_region = 'global-region'
        #dst_agent = 'global-controller'
        #jar_file_path = 'controller-1.1-SNAPSHOT.jar'
        #dst_region = 'lab'
        #dst_agent = 'controller'

        '''
        print(client.agents.get_controller_status(dst_region, dst_agent))
        if client.agents.is_controller_active(dst_region, dst_agent):
            #log = client.get_logstreamer()
            #log.connect()
            #log.update_config(dst_region, dst_agent)
            #reply = client.agents.list_plugin_agent(dst_region, dst_agent)
            #print(reply)
            #client.admin.killjvm(dst_region,dst_agent)
            #upgrade_controller_plugin(dst_region, dst_agent, jar_file_path)
            #time.sleep(60)
            #log.close()
            '''
        '''
        print(client.agents.get_controller_status(dst_region, dst_agent))
        if client.agents.is_controller_active(dst_region, dst_agent):
            #log = client.get_logstreamer()
            #log.connect()
            #log.update_config(dst_region, dst_agent)
            #reply = client.globalcontroller.get_region_resources(dst_region)
            reply = client.globalcontroller.get_agent_list()
            print(reply)
        '''

        '''
        reply = client.agents.list_plugin_agent(dst_region, 'MS4500')
            print(reply)
            for plugin in reply:
                print(plugin)
                #status_reply = client.agents.status_plugin_agent(dst_region, dst_agent, plugin['plugin_id'])
                #print(status_reply)
            time.sleep(10)
            
        '''

        '''
        dst_region = 'lab'
        dst_agent = 'controller'
        print(client.agents.get_controller_status(dst_region,dst_agent))
        #filerepo_deploy_lab(client)
        if client.agents.is_controller_active(dst_region, dst_agent):
            log = client.get_logstreamer()
            log.connect()
            log.update_config(dst_region,dst_agent)
            log.update_config(dst_region, 'MS4000')
            log.update_config(dst_region, 'MS4500')
            time.sleep(60)
            log.close()
        '''

        '''
        dst_region = "global-region"
        dst_agent = "global-controller"
        
        
        print('controller is active: ' + str(client.agents.get_controller_status(dst_region, dst_agent)))
        jar_file_path = '/Users/cody/IdeaProjects/container/target/container-1.1-SNAPSHOT.jar'
        reply = client.globalcontroller.upload_plugin_global(jar_file_path)
        print("upload" + str(reply))
        print("config: " + decompress_param(reply['configparams']))
        configparams = json.loads(decompress_param(reply['configparams']))
        reply = client.agents.add_plugin_agent(dst_region, dst_agent, configparams, None)

        dst_plugin = reply['pluginid']

        message_event_type = 'EXEC'
        message_payload = dict()
        message_payload['action'] = 'run_test'

        client.messaging.global_plugin_msgevent(False, message_event_type, message_payload, dst_region, dst_agent, dst_plugin)
        '''

        #client.admin.stopcontroller(dst_region, dst_agent)
        #reply = client.agents.get_broadcast_discovery(dst_region,'agent-controller')
        #print(reply)

        #filerepo_reboot_loop(client)
        #lorawan_reboot_loop(client)


        #reply = client.agents.get_agent_list()
        #reply = client.regions.get_region_list()
        #print(reply)


        #dst_agent = 'agent-8bf49300-402f-49b4-b3bd-2df1e9154488'

        #client.admin.restartcontroller(dst_region, dst_agent)
        # client.admin.restartframework('global-region', 'global-controller')

        #jar_file_path = '/Users/cody/IdeaProjects/controller/target/controller-1.1-SNAPSHOT.jar'
        #upgrade_controller_plugin(dst_region, dst_agent, jar_file_path)

        #launch_apps(client, 10)
        #shutdown_apps(client)


