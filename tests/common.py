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
