import glob

import pytest
from lxml import etree

from common import xml_to_dict


@pytest.mark.parametrize("snippet_file", glob.glob("snippets/*.xml"))
def test_snippet(mgr, snippet_file):
    """
    Performs the edit given in the snippet; checks that the response matches
    what the server thinks the current state of <running> is (if provided);
    performs the cleanup and ensures that the config was entirely removed
    """
    assert len(mgr.get_config(source="running").data_ele) == 0

    snippet = etree.parse(snippet_file)

    edit = snippet.xpath("//edit")[0][0]
    mgr.edit_config(target="running", config=edit)

    response = snippet.xpath("//response")
    if response:
        expected_response = response_c[0][0]
        actual_response = mgr.get_config(source="running").data_ele
        assert xml_to_dict(expected_response) == xml_to_dict(actual_response)

    cleanup = snippet.xpath("//cleanup")[0][0]
    mgr.edit_config(target="running", config=cleanup)

    assert len(mgr.get_config(source="running").data_ele) == 0
