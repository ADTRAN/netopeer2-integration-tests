import time

from ncclient.manager import connect_ssh


def wait_for(f, timeout=10, period=0.5):
    while timeout > 0:
        try:
            return f()
        except Exception:
            pass
        time.sleep(period)
        timeout -= period

    return f()


def connect_mgr():
    return connect_ssh(
        host="localhost",
        port=830,
        username="root",
        password="password",
        hostkey_verify=False,
    )


NS_MAP = {
    "nc": "urn:ietf:params:xml:ns:netconf:base:1.0",
    "sys": "urn:ietf:params:xml:ns:yang:ietf-system",
    "nc-mon": "urn:ietf:params:xml:ns:yang:ietf-netconf-monitoring",
    "test-referer": "http://example.com/netopeer2-integration-tests/test-referer",
    "test-referee": "http://example.com/netopeer2-integration-tests/test-referee",
}


def change_contact(mgr, operation, value=""):
    mgr.edit_config(
        target="running",
        config="""
    <nc:config xmlns:nc="urn:ietf:params:xml:ns:netconf:base:1.0">
      <system xmlns="urn:ietf:params:xml:ns:yang:ietf-system">
        <contact nc:operation="{op}">{value}</contact>
      </system>
    </nc:config>
    """.format(
            value=value, op=operation
        ),
    )


def get_contact(mgr):
    r = mgr.get_config(
        source="running",
        filter="""
    <filter xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">
      <system xmlns="urn:ietf:params:xml:ns:yang:ietf-system">
        <contact />
      </system>
    </filter>
    """,
    )

    node = r.data_ele.xpath("//sys:contact", namespaces=NS_MAP)
    if not node:
        return "Not Present"
    else:
        return node[0].text


def xml_to_dict(root):
    """Converts an lxml tree to a dictionary for easier comparison"""
    children = root.getchildren()
    if not children:
        return root.text

    d = {}
    for child in children:
        name = child.tag
        converted = xml_to_dict(child)
        if name not in d:
            d[name] = converted
        else:
            if not isinstance(d[name], list):
                d[name] = [d[name], converted]
            else:
                d[name].append(converted)

    return d
