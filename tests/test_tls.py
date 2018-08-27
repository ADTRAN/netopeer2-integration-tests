import shutil
import subprocess
import base64
import hashlib
import tempfile
import os
import ssl

from pyasn1_modules import pem
import pytest

from common import edit_config_dict, wait_for


def test_tls_server_missing_client_intermediate_and_leaf(mgr, temp_chains, cleanup):
    do_cert_test(
        mgr,
        temp_chains,
        client_ca_certs=[SERVER_INTR, SERVER_CA, CLIENT_INTR, CLIENT_CA],
        server_trusted_client_certs=[
            {
                "^ks:name": "TrustedClientRootCA",
                "ks:certificate": read_pem_b64(CLIENT_CA),
            }
        ],
        cert_to_name_fingerprint=cert_fingerprint(CLIENT_CA),
    )


def test_tls_server_missing_client_leaf(mgr, temp_chains, cleanup):
    do_cert_test(
        mgr,
        temp_chains,
        client_ca_certs=[SERVER_INTR, SERVER_CA, CLIENT_INTR, CLIENT_CA],
        server_trusted_client_certs=[
            {
                "^ks:name": "TrustedClientRootCA",
                "ks:certificate": read_pem_b64(CLIENT_CA),
            },
            {
                "^ks:name": "TrustedClientIntermediateCA",
                "ks:certificate": read_pem_b64(CLIENT_INTR),
            },
        ],
        cert_to_name_fingerprint=cert_fingerprint(CLIENT_CA),
    )


def test_tls_all_keys_match_root(mgr, temp_chains, cleanup):
    do_cert_test(
        mgr,
        temp_chains,
        client_ca_certs=[SERVER_INTR, SERVER_CA, CLIENT_INTR, CLIENT_CA],
        server_trusted_client_certs=[
            {
                "^ks:name": "TrustedClientRootCA",
                "ks:certificate": read_pem_b64(CLIENT_CA),
            },
            {
                "^ks:name": "TrustedClientIntermediateCA",
                "ks:certificate": read_pem_b64(CLIENT_INTR),
            },
            {
                "^ks:name": "TrustedClientLeaf",
                "ks:certificate": read_pem_b64(CLIENT_LEAF),
            },
        ],
        cert_to_name_fingerprint=cert_fingerprint(CLIENT_CA),
    )


@pytest.mark.xfail
def test_tls_client_missing_server_intermediate(mgr, temp_chains, cleanup):
    """In this case the client should ask the server for the intermediate CA"""
    do_cert_test(
        mgr,
        temp_chains,
        client_ca_certs=[SERVER_CA, CLIENT_INTR, CLIENT_CA],
        server_trusted_client_certs=[
            {
                "^ks:name": "TrustedClientRootCA",
                "ks:certificate": read_pem_b64(CLIENT_CA),
            },
            {
                "^ks:name": "TrustedClientIntermediateCA",
                "ks:certificate": read_pem_b64(CLIENT_INTR),
            },
            {
                "^ks:name": "TrustedClientLeaf",
                "ks:certificate": read_pem_b64(CLIENT_LEAF),
            },
        ],
        cert_to_name_fingerprint=cert_fingerprint(CLIENT_CA),
    )


def do_cert_test(
    mgr,
    temp_chains,
    client_ca_certs,
    server_trusted_client_certs,
    cert_to_name_fingerprint,
):
    install_keystore()
    config = {
        "ks:keystore": {
            "ks:private-keys": {
                "ks:private-key": {
                    "^ks:name": "ServerKey",
                    "ks:certificate-chains": {
                        "ks:certificate-chain": {
                            "^ks:name": "ServerKeyChain",
                            "ks:certificate": [
                                read_pem_b64(SERVER_LEAF),
                                read_pem_b64(SERVER_INTR),
                                read_pem_b64(SERVER_CA),
                            ],
                        }
                    },
                }
            },
            "ks:trusted-certificates": {
                "^ks:name": "TrustedClientCerts",
                "ks:trusted-certificate": server_trusted_client_certs,
            },
        },
        "ncs:netconf-server": {
            "ncs:listen": {
                "ncs:endpoint": {
                    "^ncs:name": "EndpointTLS",
                    "ncs:tls": {
                        "ncs:address": "0.0.0.0",
                        "ncs:port": "6513",
                        "ncs:certificates": {
                            "ncs:certificate": {"ncs:name": "ServerKeyChain"}
                        },
                        "ncs:client-auth": {
                            "ncs:trusted-ca-certs": "TrustedClientCerts",
                            "ncs:cert-maps": {
                                "ncs:cert-to-name": {
                                    "^ncs:id": "1",
                                    "ncs:fingerprint": cert_to_name_fingerprint,
                                    # I don't know why the NETCONF server requires the xmlns right
                                    # here instead of on the config node
                                    'ncs:map-type@xmlns:x509c2n="urn:ietf:params:xml:ns:yang:ietf-x509-cert-to-name"': "x509c2n:specified",
                                    "ncs:name": "root",
                                }
                            },
                        },
                    },
                }
            }
        },
    }
    edit_config_dict(mgr, config)

    def openssl_connect():
        with open(os.devnull, "r") as n:
            subprocess.check_call(
                "openssl s_client -connect localhost:6513 -CAfile {ca_certs} -cert {certfile} -key {keyfile} "
                "-state -debug -showcerts -verify_return_error -verify 1".format(
                    keyfile=CLIENT_LEAF_KEY,
                    certfile=CLIENT_LEAF,
                    ca_certs=temp_chains.create(client_ca_certs),
                ),
                shell=True,
                stdin=n,
            )

    wait_for(openssl_connect, timeout=30, period=0.5)

    # TODO: Connect with a TLS-aware client once we get one


def install_keystore():
    subprocess.check_call(["mkdir", "-p", "/etc/keystored/keys"])
    shutil.copy(SERVER_LEAF_KEY, "/etc/keystored/keys/ServerKey.pem")
    shutil.copy(SERVER_LEAF, "/etc/keystored/keys/ServerKey.pub.pem")


def read_pem_b64(path):
    with open(path, "r") as f:
        bits = pem.readPemFromFile(f)
        return base64.b64encode(bits).decode("utf-8")


def cert_fingerprint(path):
    with open(path, "r") as f:
        bits = pem.readPemFromFile(f)
        digest = hashlib.sha256(bits).hexdigest()
        chunked = ":".join(digest[i : i + 2] for i in range(0, len(digest), 2))
        # 04 is the TLS Hash ID
        return "04:" + chunked


class TempChains:
    def __init__(self):
        self.temp_files = []

    def create(self, certs):
        (_, p) = tempfile.mkstemp()
        with open(p, "w") as f:
            for cert in certs:
                with open(cert, "r") as src:
                    f.write(src.read())
        self.temp_files.append(p)
        return p

    def clean(self):
        for p in self.temp_files:
            os.remove(p)
        self.temp_files = []


@pytest.fixture()
def temp_chains():
    t = TempChains()
    yield t
    t.clean()


@pytest.fixture()
def cleanup(mgr):
    yield
    edit_config_dict(
        mgr,
        {
            "ks:keystore": {
                "ks:private-keys": {
                    "ks:private-key": {
                        "@nc:operation": "remove",
                        "^ks:name": "ServerKey",
                    }
                },
                "ks:trusted-certificates": {
                    "@nc:operation": "remove",
                    "^ks:name": "TrustedClientCerts",
                },
            },
            "ncs:netconf-server": {
                "ncs:listen": {
                    "ncs:endpoint": {
                        "@nc:operation": "remove",
                        "^ncs:name": "EndpointTLS",
                    }
                }
            },
        },
    )


SERVER_CA = "pki/server/root-ca/certs/ca.crt"
SERVER_INTR = "pki/server/intermediate/certs/intermediate.crt"
SERVER_LEAF = "pki/server/out/Server.crt"
SERVER_LEAF_KEY = "pki/server/out/Server.key"

CLIENT_CA = "pki/client/root-ca/certs/ca.crt"
CLIENT_INTR = "pki/client/intermediate/certs/intermediate.crt"
CLIENT_LEAF = "pki/client/out/Client.crt"
CLIENT_LEAF_KEY = "pki/client/out/Client.key"
