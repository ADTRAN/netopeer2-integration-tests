def test_basic_edit(mgr):
    mgr.edit_config(
        target="running",
        config="""
    <config xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">
      <system xmlns="urn:ietf:params:xml:ns:yang:ietf-system">
        <contact>TestContact</contact>
      </system>
    </config>
    """,
    )
