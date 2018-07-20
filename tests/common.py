from ncclient.manager import connect_ssh


def wait_for(f, timeout=10, period=0.5):
    import time

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
