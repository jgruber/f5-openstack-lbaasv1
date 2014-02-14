from netaddr import ip
from suds import WebFault

from f5.bigip.bigip_interfaces import domain_address
from f5.bigip.bigip_interfaces import icontrol_folder
# Networking - Routing


class Route(object):
    def __init__(self, bigip):
        self.bigip = bigip
        # add iControl interfaces if they don't exist yet
        self.bigip.icontrol.add_interfaces(['Networking.RouteTableV2',
                                            'Networking.RouteDomainV2'])

        # iControl helper objects
        self.net_route = self.bigip.icontrol.Networking.RouteTableV2
        self.net_domain = self.bigip.icontrol.Networking.RouteDomainV2

    @domain_address
    def create(self, name=None, dest_ip_address=None, dest_mask=None,
               gw_ip_address=None, folder='Common'):
        if not self.exists(name=None, folder=folder) and \
           ip(dest_ip_address) and ip(gw_ip_address):
            dest = self.net_route.typefactory.create(
                    'Networking.RouteTableV2.RouteDestination')
            dest.address = dest_ip_address
            dest.netmask = dest_mask
            attr = self.net_route.typefactory.create(
                    'Networking.RouteTableV2.RouteAttribute')
            attr.gateway = gw_ip_address
            self.net_route2.create_static_route([name], [dest], [attr])

    def delete(self, name=None, folder='Common'):
        if self.exists(name=name, folder=folder):
            self.net_route2.delete_static_route([name])

    def get_vlans_in_domain(self, folder='Common'):
        return self.net_domain.get_vlan([self._get_domain_name(folder)])[0]

    @icontrol_folder
    def add_vlan_to_domain(self, name=None, folder='Common'):
        if not name in self.get_vlans_in_domain(folder):
            rd_entry_seq = self.net_domain.typefactory.create(
                                            'Common.StringSequence')
            rd_entry_seq.values = [name]
            rd_entry_seq_seq = self.net_domain.typefactory.create(
                                            'Common.StringSequenceSequence')
            rd_entry_seq_seq.values = [rd_entry_seq]
            self.net_domain.add_vlan([self._get_domain_name(folder)],
                                     rd_entry_seq_seq)

    @icontrol_folder
    def create_domain(self, folder='Common'):
        ids = [self._get_next_domain_id()]
        domains = [self._get_domain_name(folder)]
        self.net_domain.create(domains, ids, [[]])
        return ids[0]

    @icontrol_folder
    def delete_domain(self, folder='Common'):
        domains = [self._get_domain_name(folder)]
        try:
            self.net_domain.delete_route_domain(domains)
            self.bigip.system.delete_folder(folder)
        except WebFault as wf:
            if "is referenced" in str(wf.message):
                return
            if "All objects must be removed" in str(wf.message):
                return

    @icontrol_folder
    def get_domain(self, folder='Common'):
        try:
            return self.net_domain.get_identifier(
                 [self._get_domain_name(folder)])[0]
        except WebFault as wf:
            if "was not found" in str(wf.message):
                return self.create_domain(folder)

    @icontrol_folder
    def exists(self, name=None, folder='Common'):
        if name in self.net_route2.get_static_route_list():
            return True

    def _get_domain_name(self, folder='Common'):
        folder = folder.replace('/', '')
        return '/' + folder + '/' + folder

    def _get_next_domain_id(self):
        self.bigip.system.set_folder('/')
        self.bigip.system.sys_session.set_recursive_query_state(1)
        all_route_domains = self.net_domain.get_list()
        if len(all_route_domains) > 1:
            all_identifiers = sorted(
                self.net_domain.get_identifier(all_route_domains))
            self.bigip.system.set_folder('Common')
            self.bigip.system.sys_session.set_recursive_query_state(0)
        else:
            self.bigip.system.set_folder('Common')
            self.bigip.system.sys_session.set_recursive_query_state(0)
            return 1
        lowest_available_index = 1
        for i in range(len(all_identifiers)):
            if all_identifiers[i] < lowest_available_index:
                if len(all_identifiers) > (i + 1):
                    if all_identifiers[i + 1] > lowest_available_index:
                        return lowest_available_index
                    else:
                        lowest_available_index = lowest_available_index + 1
        else:
            return lowest_available_index
