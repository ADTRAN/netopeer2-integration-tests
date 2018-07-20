import subprocess

import pytest

from common import wait_for, connect_mgr


@pytest.fixture(scope="session")
def services():
    """Start the services"""
    subprocess.check_call("echo root:password | chpasswd", shell=True)
    subprocess.check_call("supervisord")

    wait_for(connect_mgr, timeout=60, period=0.5).close_session()


@pytest.fixture()
def mgr(services):
    """Connect to the NETCONF server"""
    return connect_mgr()
