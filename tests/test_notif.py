import requests
from ncclient.xml_ import to_ele

from common import send_notification, NS_MAP


def test_basic_notification(mgr):
    mgr.dispatch(
        to_ele(
            """
            <create-subscription xmlns="urn:ietf:params:xml:ns:netconf:notification:1.0">
              <filter>
                <hardware-state-change xmlns="urn:ietf:params:xml:ns:yang:ietf-hardware" />
              </filter>
            </create-subscription>
            """
        )
    )
    send_notification({"xpath": "/ietf-hardware:hardware-state-change", "values": []})
    n = mgr.take_notification(timeout=10)
    assert n.notification_ele.xpath(
        "//ietf-hw:hardware-state-change", namespaces=NS_MAP
    )
