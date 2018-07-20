from common import change_contact, get_contact


def test_basic_edit(mgr):
    assert get_contact(mgr) == "Not Present"
    change_contact(mgr, "merge", "TestValue")
    assert get_contact(mgr) == "TestValue"
    change_contact(mgr, "delete", "TestValue")
    assert get_contact(mgr) == "Not Present"
