from server import RestServer
from helper import *

REST_SCHEMA = {
    'login': '/auth/login',
    'logout': '/auth/logout',
    'status': '/status',
    'list_templates': '/list/templates/',
    'get_user_info': '/auth',
    'create_lab': '/labs',
    'create_node': '/labs/{lab_name}/nodes',
    'delete_lab': '/labs/{lab_name}',
    'get_all_nodes': '/labs/{lab_name}/nodes',
    'create_net': '/labs/{lab_name}/networks',
    'get_nets': '/labs/{lab_name}/networks',
    'connect_interface': '/labs/{lab_name}/nodes/{node_id}/interfaces',
    'get_users': '/users/',
    'delete_node': '/labs/{lab_name}/nodes/{node_id}',
    'start_all_nodes': '/labs/{lab_name}/nodes/start',
    'stop_all_nodes': '/labs/{lab_name}/nodes/stop',
}


class EveServer(RestServer):

    def __init__(self, address):
        super(EveServer, self).__init__(address)
        self.user, self.pwd = '', ''

    def login(self, user, pwd):
        api_call = REST_SCHEMA['login']
        payload = {
            "username": user,
            "password": pwd
        }
        resp = self.add_object(api_call, data=payload)
        self.set_cookies(resp.cookies)
        self.set_credentials(user, pwd)
        return resp

    def logout(self):
        api_call = REST_SCHEMA['logout']
        resp = self.get_object(api_call)
        return resp

    def get_status(self):
        api_call = REST_SCHEMA['status']
        resp = self.get_object(api_call)
        return resp

    def get_templates(self):
        api_call = REST_SCHEMA['list_templates']
        resp = self.get_object(api_call)
        return resp

    def get_user_info(self):
        api_call = REST_SCHEMA['get_user_info']
        resp = self.get_object(api_call)
        return resp

    def get_users(self):
        api_call = REST_SCHEMA['get_users']
        api_url = api_call.format(api_call)
        resp = self.get_object(api_url)
        return resp

    def create_lab(self, name):
        api_call = REST_SCHEMA['create_lab']
        payload = {
           "path": "/",
           "name": name,
           "version": "1"
        }
        self.add_object(api_call, data=payload)
        return EveLab(self, name)

    def get_lab(self, name):
        return EveLab(self, name)

    def delete_lab(self, labname):
        api_call = REST_SCHEMA['delete_lab']
        api_url = api_call.format(api_call, lab_name=append_eve(labname))
        resp = self.del_object(api_url)
        return resp


class EveLab(object):

    def __init__(self, eve, name):
        self.name = name
        self.eve = eve

    def create_node(self, device):
        api_call = REST_SCHEMA['create_node']
        api_url = api_call.format(api_call, lab_name=append_eve(self.name))
        payload = device.to_json()
        self.eve.add_object(api_url, data=payload)
        return EveNode(self, device)

    def get_node(self, device):
        return EveNode(self, device)

    def get_nodes(self):
        api_call = REST_SCHEMA['get_all_nodes']
        api_url = api_call.format(api_call, lab_name=append_eve(self.name))
        resp = self.eve.get_object(api_url)
        return resp

    def get_net(self, name, net_type='bridge'):
        return EveNet(self, name, net_type)

    def create_net(self, name, net_type='bridge'):
        api_call = REST_SCHEMA['create_net']
        api_url = api_call.format(api_call, lab_name=append_eve(self.name))
        payload = {'type': net_type, 'name': name}
        self.eve.add_object(api_url, data=payload)
        return EveNet(self, name, net_type)

    def get_nets(self):
        api_call = REST_SCHEMA['get_nets']
        api_url = api_call.format(api_call, lab_name=append_eve(self.name))
        resp = self.eve.get_object(api_url)
        return resp

    def start_all_nodes(self):
        api_call = REST_SCHEMA['start_all_nodes']
        api_url = api_call.format(api_call, lab_name=append_eve(self.name))
        resp = self.eve.get_object(api_url)
        return resp

    def stop_all_nodes(self):
        api_call = REST_SCHEMA['stop_all_nodes']
        api_url = api_call.format(api_call, lab_name=append_eve(self.name))
        resp = self.eve.get_object(api_url)
        return resp

    def delete_node(self, node_id):
        api_call = REST_SCHEMA['delete_node']
        api_url = api_call.format(api_call, lab_name=append_eve(self.name), node_id=node_id)
        resp = self.eve.del_object(api_url)
        return resp

    def del_all_nodes(self):
        node_dict = self.get_nodes().json().get('data', {})
        for node_id in node_dict:
            self.delete_node(node_id)
        return None

    def cleanup(self):
        self.stop_all_nodes()
        self.del_all_nodes()
        return None


class EveNode(object):

    def __init__(self, lab, device):
        self.eve = lab.eve
        self.lab = lab
        self.device = device
        self.node = self._get_node()
        self.id = self.node['id']
        self.url = self.node['url']
        self.device.set_url(self.url)
        self.intf_to_net = dict()

    def _get_node(self):
        nodes = self.lab.get_nodes().json().get('data', {})
        return get_obj_by_name(nodes, self.device.name)

    def connect_interface(self, intf_name, net):
        api_call = REST_SCHEMA['connect_interface']
        api_url = api_call.format(api_call, lab_name=append_eve(self.lab.name), node_id=self.id)
        self.intf_to_net[intf_name] = net.name
        payload = {self.device.get_intf_id(intf_name): net.id}
        resp = self.eve.update_object(api_url, data=payload)
        return resp

    def connect_node(self, local_intf, other_node, other_intf):
        net_local = self.intf_to_net.get(local_intf)
        net_other = other_node.intf_to_net.get(other_intf)
        if net_local:
            net = self.lab.get_net(net_local)
        elif net_other:
            net = self.lab.get_net(net_other)
        else:
            net = self.lab.create_net(name='_'.join([self.device.name, other_node.device.name]))
        resp1 = self.connect_interface(local_intf, net)
        resp2 = other_node.connect_interface(other_intf, net)
        return resp1, resp2

    def get_next_intf(self):
        return self.device.get_next_intf()

    def configure(self, text):
        return self.device.send_config(text)


class EveNet(object):

    def __init__(self, lab, name, net_type):
        self.eve, self.lab, self.name = lab.eve, lab, name
        self.net = self._get_net()
        self.id = self.net['id']

    def _get_net(self):
        nets = self.lab.get_nets().json().get('data', {})
        return get_obj_by_name(nets, self.name)
