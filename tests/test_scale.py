import pytest
import time
import os
from lxml import etree
from ncclient.operations.errors import TimeoutExpiredError


def pretty_xml(xml):
    """ Returns a beautified XML string """
    try:
        #parser = etree.XMLParser(remove_blank_text=True)
        tree = etree.fromstring(xml.encode('utf-8'))
        return etree.tostring(tree, pretty_print=True).decode()
    except:
        print(f"ERROR pretty_xml() xml:{xml}")
        raise


def prepend_config(xml):
    return pretty_xml(
        f'''<nc:config xmlns:nc="urn:ietf:params:xml:ns:netconf:base:1.0">{xml}</nc:config>'''
    )


###############################################################################
# ietf-interfaces
###############################################################################


def prepend_interfaces(xml):
    return f"""<interfaces xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces">{xml}</interfaces>"""


def create_vlan_subinterface_single_tagged(interface, vlanid):
    return f"""
        <interface nc:operation="create">
          <name>{interface}.{vlanid}</name>
          <type xmlns:ift="urn:bbf:yang:bbf-if-type">ift:vlan-sub-interface</type>
          <enabled>true</enabled>
          <subif-lower-layer xmlns="urn:bbf:yang:bbf-sub-interfaces">
              <interface>{interface}</interface>
          </subif-lower-layer>
          <inline-frame-processing xmlns="urn:bbf:yang:bbf-sub-interfaces">
            <ingress-rule>
              <rule>
                <name>1</name>
                <priority>1</priority>
                <flexible-match>
                  <match-criteria xmlns="urn:bbf:yang:bbf-sub-interface-tagging">
                    <tag>
                      <index>0</index>
                      <dot1q-tag>
                        <tag-type xmlns:q="urn:bbf:yang:bbf-dot1q-types">q:s-vlan</tag-type>
                        <vlan-id>{vlanid}</vlan-id>
                      </dot1q-tag>
                    </tag>
                  </match-criteria>
                </flexible-match>
              </rule>
            </ingress-rule>
          </inline-frame-processing>
        </interface>"""


def create_interface_base(iface):
    return f"""
        <interface>
          <name>{iface}</name>
          <enabled>true</enabled>
          <type xmlns:ianaift="urn:ietf:params:xml:ns:yang:iana-if-type">ianaift:ethernetCsmacd</type>
        </interface>
    """


def delete_interface(interface):
    return f"""<interface nc:operation='remove'>
                 <name>{interface}</name>
               </interface>"""


def delete_vlan_subinterface_single_tagged(interface, vlanid):
    return delete_interface(f"{interface}.{vlanid}")


###############################################################################
# bbf-forwarder
###############################################################################


def prepend_forwarding(xml):
    return f"""<forwarding xmlns="urn:bbf:yang:bbf-l2-forwarding">{xml}</forwarding>"""

def prepend_forwarding_databases(xml):
    return f"""<forwarding-databases>{xml}</forwarding-databases>"""

def create_forwarding_databases_database(name):
    return f"""
        <forwarding-database nc:operation="merge">
            <name>{name}</name>
        </forwarding-database>"""

def prepend_forwarding_forwarders(xml):
    return f"""<forwarders>{xml}</forwarders>"""

def remove_forwarders():
    return f"""<forwarders nc:operation='remove'></forwarders>"""

def xml_forwarder(fwdr_name: str, subifs: list, db=None) -> str:
    """This function does not create a forwarder. It *constructs* the raw xml for:
        A single forwarder with any number of ports, and optional mac-learning database.
    """
    mac_learning = "" if db is None else f"""
        <mac-learning>
            <forwarding-database>{db}</forwarding-database>
        </mac-learning>"""
    ports = "".join([f"""
        <port>
            <name>{subif}</name>
            <sub-interface>{subif}</sub-interface>
        </port>"""
    for subif in subifs])

    return f"""
        <forwarder nc:operation="create">
            <name>{fwdr_name}</name>
                <ports>
                    {ports}
                </ports>
                {mac_learning}
        </forwarder>"""


def create_forwarding_forwarders_forwarder(database, subif1, subif2):
    return f"""
       <forwarder nc:operation="create">
          <name>fwd-{subif1}-{subif2}</name>
		  <ports>
			<port>
              <name>{subif1}</name>
              <sub-interface>{subif1}</sub-interface>
            </port>
			<port>
              <name>{subif2}</name>
              <sub-interface>{subif2}</sub-interface>
            </port>
          </ports>
          <mac-learning>
            <forwarding-database>{database}</forwarding-database>
          </mac-learning>
       </forwarder>"""


def delete_forwarding_forwarders_forwarder(database, subif1, subif2):
    return f"""
       <forwarder nc:operation="remove">
          <name>fwd-{subif1}-{subif2}</name>
       </forwarder>"""


def create_subifs_forwarding_forwarders_forwarder(database, vlanid, interfaces):
    port_str = ""

    for interface in interfaces:
        port_str += f"""
			<port>
              <name>{interface}.{vlanid}</name>
              <sub-interface>{interface}.{vlanid}</sub-interface>
            </port>"""

    return f"""
       <forwarder nc:operation="create">
          <name>{vlanid}</name>
		  <ports>{port_str}
          </ports>
          <mac-learning>
            <forwarding-database>{database}</forwarding-database>
          </mac-learning>
       </forwarder>"""


def delete_subifs_forwarding_forwarders_forwarder(database, vlanid):
    return f"""
       <forwarder nc:operation="remove">
          <name>{vlanid}</name>
       </forwarder>"""


###############################################################################
# single operations
###############################################################################


def create_interfaces_forwarders_single_tagged(if1, if2, vlanid):
    return prepend_config(
        prepend_interfaces(
            create_vlan_subinterface_single_tagged(if1, vlanid) +
            create_vlan_subinterface_single_tagged(if2, vlanid)
        ) +
        prepend_forwarding(
            prepend_forwarding_databases(
                create_forwarding_databases_database("FDB1")
            ) +
            prepend_forwarding_forwarders(
                create_forwarding_forwarders_forwarder("FDB1", f"{if1}.{vlanid}", f"{if2}.{vlanid}")
            )
        )
    )


def delete_interfaces_forwarders_single_tagged(if1, if2, vlanid):
    return prepend_config(
        prepend_forwarding(
            prepend_forwarding_forwarders(
                delete_forwarding_forwarders_forwarder("FDB1", f"{if1}.{vlanid}", f"{if2}.{vlanid}")
            )
        ) +
        prepend_interfaces(
            delete_vlan_subinterface_single_tagged(if1, vlanid) +
            delete_vlan_subinterface_single_tagged(if2, vlanid)
        )
    )


###############################################################################
# bulk operations
###############################################################################


def bulk_create_interfaces_base(ifaces):
    return prepend_config(
        prepend_interfaces(
            "".join([create_interface_base(iface)
                     for iface in ifaces])
        )
    )


def bulk_delete_interfaces_base(ifaces):
    return prepend_config(
        prepend_interfaces(
            "".join([delete_interface(iface)
                     for iface in ifaces])
        )
    )


def bulk_create_interfaces_forwarders_single_tagged(if1, if2, vlanids):
    return prepend_config(
        prepend_interfaces(
            "".join([create_vlan_subinterface_single_tagged(if1, vlanid)
                     for vlanid in vlanids]) +
            "".join([create_vlan_subinterface_single_tagged(if2, vlanid)
                     for vlanid in vlanids])
        ) +
        prepend_forwarding(
            prepend_forwarding_databases(
                create_forwarding_databases_database("FDB1")
            ) +
            prepend_forwarding_forwarders(
                "".join([create_forwarding_forwarders_forwarder("FDB1", f"{if1}.{vlanid}", f"{if2}.{vlanid}")
                         for vlanid in vlanids])
            )
        )
    )


def bulk_delete_interfaces_forwarders_single_tagged(if1, if2, vlanids):
    return prepend_config(
        prepend_forwarding(
            prepend_forwarding_forwarders(
                "".join([delete_forwarding_forwarders_forwarder("FDB1", f"{if1}.{vlanid}", f"{if2}.{vlanid}")
                         for vlanid in vlanids])
            )
        ) +
        prepend_interfaces(
            "".join([delete_vlan_subinterface_single_tagged(if1, vlanid)
                        for vlanid in vlanids]) +
            "".join([delete_vlan_subinterface_single_tagged(if2, vlanid)
                        for vlanid in vlanids])
        )
    )


###############################################################################
# the testcases
###############################################################################


SkipScaleTests = True


BaseInterfaces = ['ethernet 0/1:1', 'ethernet 0/2:1']
BenchMarkFile = '/var/log/benchmark.log'


class BenchMark:
    def __init__(self):
        self.start = 0.0
        self.stop = 0.0
        self.elapsed = 0.0

    def __enter__(self):
        self.start = time.time()
        return self

    def __exit__(self, exctyp, excval, exctrc):
        self.stop = time.time()
        self.elapsed = self.stop-self.start
        return False

@pytest.fixture(scope='session')
def setup_log():
    if os.path.exists(BenchMarkFile):
        os.remove(BenchMarkFile)


@pytest.fixture()
def setup(mgr):
    mgr.edit_config(
        target='running',
        config=bulk_create_interfaces_base(BaseInterfaces)
    )


@pytest.fixture()
def cleanup(mgr):
    yield
    mgr.edit_config(
        target='running',
        config=bulk_delete_interfaces_base(BaseInterfaces)
    )


@pytest.mark.skipif(SkipScaleTests, reason='long runner')
@pytest.mark.parametrize('vlan_count', [10, 20, 50, 100, ])
def test_scale_single(setup_log, mgr, request, setup, cleanup, vlan_count):
    with open(BenchMarkFile, 'a') as f:

        f.write('%s create:' % request.node.name)
        with BenchMark() as b:
            for vlan in range(0, vlan_count):
                try:
                    mgr.edit_config(
                        target='running',
                        config=create_interfaces_forwarders_single_tagged(BaseInterfaces[0], BaseInterfaces[1], vlan+1),
                    )
                except TimeoutExpiredError as e:
                    f.write(' (%s)' % str(e))
        f.write(' %.1f sec\n' % b.elapsed)

        f.write('%s delete:' % request.node.name)
        with BenchMark() as b:
            for vlan in range(0, vlan_count):
                try:
                    mgr.edit_config(
                        target='running',
                        config=delete_interfaces_forwarders_single_tagged(BaseInterfaces[0], BaseInterfaces[1], vlan+1),
                    )
                except TimeoutExpiredError as e:
                    f.write(' (%s)' % str(e))
        f.write(' %.1f sec\n' % b.elapsed)


@pytest.mark.skipif(SkipScaleTests, reason='long runner')
@pytest.mark.parametrize('vlan_count', [10, 20, 50, 100, 200, 500, 1000, ])
def test_scale_bulk(setup_log, mgr, request, setup, cleanup, vlan_count):
    with open(BenchMarkFile, 'a') as f:

        f.write('%s create:' % request.node.name)
        with BenchMark() as b:
            try:
                mgr.edit_config(
                    target='running',
                    config=bulk_create_interfaces_forwarders_single_tagged(BaseInterfaces[0], BaseInterfaces[1], range(1, vlan_count+1)),
                )
            except TimeoutExpiredError as e:
                f.write(' (%s)' % str(e))
        f.write(' %.1f sec\n' % b.elapsed)

        f.write('%s delete:' % request.node.name)
        with BenchMark() as b:
            try:
                mgr.edit_config(
                    target='running',
                    config=bulk_delete_interfaces_forwarders_single_tagged(BaseInterfaces[0], BaseInterfaces[1], range(1, vlan_count+1)),
                )
            except TimeoutExpiredError as e:
                f.write(' (%s)' % str(e))
        f.write(' %.1f sec\n' % b.elapsed)


@pytest.mark.skipif(SkipScaleTests, reason='long runner')
@pytest.mark.parametrize('vlan_count', [10, 20, 50, 100, 200, 500, 1000, ])
def test_scale_bulk_plus_one(setup_log, mgr, request, setup, cleanup, vlan_count):
    with open(BenchMarkFile, 'a') as f:

        f.write('%s create:' % request.node.name)
        with BenchMark() as b:
            try:
                mgr.edit_config(
                    target='running',
                    config=bulk_create_interfaces_forwarders_single_tagged(BaseInterfaces[0], BaseInterfaces[1], range(1, vlan_count+1)),
                )
                mgr.edit_config(
                    target='running',
                    config=create_interfaces_forwarders_single_tagged(BaseInterfaces[0], BaseInterfaces[1], vlan_count+1),
                )
            except TimeoutExpiredError as e:
                f.write(' (%s)' % str(e))
        f.write(' %.1f sec\n' % b.elapsed)

        f.write('%s delete:' % request.node.name)
        with BenchMark() as b:
            try:
                mgr.edit_config(
                    target='running',
                    config=delete_interfaces_forwarders_single_tagged(BaseInterfaces[0], BaseInterfaces[1], vlan_count+1),
                )
                mgr.edit_config(
                    target='running',
                    config=bulk_delete_interfaces_forwarders_single_tagged(BaseInterfaces[0], BaseInterfaces[1], range(1, vlan_count+1)),
                )
            except TimeoutExpiredError as e:
                f.write(' (%s)' % str(e))
        f.write(' %.1f sec\n' % b.elapsed)


