import pytest
from common import (
    install_module, 
    uninstall_module, 
    enable_feature,
    disable_feature,
    netconf_logger,
)
from ncclient.operations.rpc import RPCError
from lxml import etree


NcConfig = """
<nc:config xmlns:nc="urn:ietf:params:xml:ns:netconf:base:1.0">
{}
</nc:config>
"""

ErrorResponse1 = """
    <config xmlns="urn:issue:error:response">
        <password>$0$valid</password>
    </config>
"""

ErrorResponse2 = """
    <config xmlns="urn:issue:error:response">
        <password>malformed</password>
    </config>
"""

ErrorResponse3 = """
    <config xmlns="urn:issue:error:response">
        <passsword>$0$valid</passsword>
    </config>
"""

FreeStyleXml1 = """
    <config xmlns="urn:issue:parse:xml">
        <color-leaf>green</color-leaf>
    </config>
"""

FreeStyleXml2 = """
    <config xmlns="urn:issue:parse:xml">
        <color-leaf>red </color-leaf>
    </config>
"""

FreeStyleXml3 = """
    <config xmlns="urn:issue:parse:xml">
        <color-leaf>blue
        </color-leaf>
    </config>
"""

FreeStyleXml4 = """
    <config xmlns="urn:issue:parse:xml">
        <color-leaf>
        red</color-leaf>
    </config>
"""

FreeStyleXml5 = """
    <config xmlns="urn:issue:parse:xml">
        <color-leaf> green</color-leaf>
    </config>
"""

IssueNamespace = """
    <root xmlns="urn:issue:namespace">
        <my-char>a</my-char>
        <my-color xmlns="urn:issue:namespace:aug">green</my-color>
    </root>
"""


def prepend_config(xml):
    xml = NcConfig.format(xml)
    print(xml)
    return xml


def test_issue_augment_uses_when():
    install_module('issue-augment-uses-when')
    uninstall_module('issue-augment-uses-when')
    # issue-augment-uses-when-grp already uninstalled
    uninstall_module('issue-augment-uses-when-cnt')


@pytest.mark.xfail(reason='issue libyang#1795 not yet fixed')
def test_issue_install():
    install_module('issue-install-cfm-ala')
    install_module('issue-install-que')
    uninstall_module('issue-install-que')
    uninstall_module('issue-install-cfm-ala')
    uninstall_module('issue-install-cfm')
    uninstall_module('issue-install-ala')


def test_issue_if_feature():
    install_module('issue-if-feature-pck')
    install_module('issue-if-feature')
    install_module('issue-if-feature-tm')
    enable_feature('issue-if-feature-tm', 'root')
    enable_feature('issue-if-feature-pck', 'packages')
    enable_feature('issue-if-feature-grp', 'root-value')
    disable_feature('issue-if-feature-grp', 'root-value')
    disable_feature('issue-if-feature-pck', 'packages')
    disable_feature('issue-if-feature-tm', 'root')
    uninstall_module('issue-if-feature-pck')
    uninstall_module('issue-if-feature-grp')
    uninstall_module('issue-if-feature-tm')
    uninstall_module('issue-if-feature')


def test_issue_error_response(mgr, request):
    netconf_logger.start(request)
    # create invalid element
    try:
        mgr.edit_config(
            target='running',
            config=prepend_config(ErrorResponse3)
        )
        assert False
    except RPCError as e:
        print('REPLY:', etree.tostring(e.xml, pretty_print=True).decode('UTF-8'))
        ns = {'ns': 'urn:ietf:params:xml:ns:netconf:base:1.0'}
        etag = e.xml.find('.//ns:error-tag', ns) 
        esev = e.xml.find('.//ns:error-severity', ns) 
        emsg = e.xml.find('.//ns:error-message', ns)
        assert etag is not None and etag.text == 'unknown-element'
        assert esev is not None and esev.text == 'error'
        assert emsg is not None and emsg.text
    # create invalid value
    try:
        mgr.edit_config(
            target='running',
            config=prepend_config(ErrorResponse2)
        )
        assert False
    except RPCError as e:
        print('REPLY:', etree.tostring(e.xml, pretty_print=True).decode('UTF-8'))
        ns = {'ns': 'urn:ietf:params:xml:ns:netconf:base:1.0'}
        etag = e.xml.find('.//ns:error-tag', ns) 
        esev = e.xml.find('.//ns:error-severity', ns) 
        emsg = e.xml.find('.//ns:error-message', ns)
        assert etag is not None and etag.text == 'invalid-value'
        assert esev is not None and esev.text == 'error'
        assert emsg is not None and emsg.text
    # create valid value
    mgr.edit_config(
        target='running',
        config=prepend_config(ErrorResponse1)
    )
    # replace invalid value
    try:
        mgr.edit_config(
            target='running',
            config=prepend_config(ErrorResponse2)
        )
        assert False
    except RPCError as e:
        print('REPLY:', etree.tostring(e.xml, pretty_print=True).decode('UTF-8'))
        ns = {'ns': 'urn:ietf:params:xml:ns:netconf:base:1.0'}
        etag = e.xml.find('.//ns:error-tag', ns) 
        esev = e.xml.find('.//ns:error-severity', ns) 
        emsg = e.xml.find('.//ns:error-message', ns)
        assert etag is not None and etag.text == 'invalid-value'
        assert esev is not None and esev.text == 'error'
        assert emsg is not None and emsg.text
    netconf_logger.stop(request)


@pytest.mark.xfail(reason='no issue yet: when parsing XML values are not stripped')
def test_issue_parse_xml(mgr, request):
    netconf_logger.start(request)
    mgr.edit_config(
        target='running',
        config=prepend_config(FreeStyleXml1)
    )
    try:
        mgr.edit_config(
            target='running',
            config=prepend_config(FreeStyleXml2)
        )
    except RPCError as e:
        print('REPLY:', etree.tostring(e.xml, pretty_print=True).decode('UTF-8'))
    try:
        mgr.edit_config(
            target='running',
            config=prepend_config(FreeStyleXml3)
        )
    except RPCError as e:
        print('REPLY:', etree.tostring(e.xml, pretty_print=True).decode('UTF-8'))
    try:
        mgr.edit_config(
            target='running',
            config=prepend_config(FreeStyleXml4)
        )
    except RPCError as e:
        print('REPLY:', etree.tostring(e.xml, pretty_print=True).decode('UTF-8'))
    try:
        mgr.edit_config(
            target='running',
            config=prepend_config(FreeStyleXml5)
        )
    except RPCError as e:
        print('REPLY:', etree.tostring(e.xml, pretty_print=True).decode('UTF-8'))
    netconf_logger.stop(request)
    assert False


@pytest.mark.xfail(reason='issue libyang#1792 not yet fixed')
def test_issue_namespace(mgr, request):
    netconf_logger.start(request)
    mgr.edit_config(
        target='running',
        config=prepend_config(IssueNamespace)
    )
    reply = mgr.get_config(
        source='running',
        filter=('subtree', '<root xmlns="urn:issue:namespace"/>')
    ).data_ele.find('{urn:issue:namespace}root')
    request = etree.fromstring(IssueNamespace)
    netconf_logger.stop(request)
    print('REQUEST:', etree.tostring(request, pretty_print=True).decode('UTF-8'))
    print('REPLY:  ', etree.tostring(reply, pretty_print=True).decode('UTF-8'))
    assert reply == request


