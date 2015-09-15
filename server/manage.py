#!/usr/bin/env python2

"""
Management console
"""

import click
from IPython import embed
from zerodb import DB
from zerodb.storage import client_storage
from zerodb.transform import init_crypto
import logging


@click.command()
@click.option("--username", help="Admin username")
@click.option("--passphrase", help="Admin passphrase or hex private key")
@click.option("--sock", default="localhost:8001", help="Storage server socket (TCP or UNIX)")
def run(username, passphrase, sock):
    logging.basicConfig()
    username = str(username)
    passphrase = str(passphrase)
    sock = str(sock)
    if not sock.startswith("/"):
        sock = (sock.split(":")[0], int(sock.split(":")[1]))
    DB.auth_module.register_auth()
    DB.encrypter.register_class(default=True)
    init_crypto(passphrase=passphrase)

    def useradd(username, password):
        storage.add_user(username, password)

    def userdel(username):
        storage.del_user(username)

    def chpass(username, password):
        storage.change_key(username, password)

    print "Usage:"
    print "========"
    print "useradd(username, password) - add user"
    print "userdel(username) - remove user"
    print "chpass(username, password) - change passphrase"
    print "exit() or ^D - exit"

    storage = client_storage(sock,
            username=username, password=passphrase, realm="ZERO")
    embed(display_banner=False)


if __name__ == "__main__":
    run()
