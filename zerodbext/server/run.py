#!/usr/bin/env python2

"""
Simple script to run db server.
You can specify db path and socket name (can be UNIX or TCP socket).
"""

import click
from os import getcwd, path
from zerodb.permissions import elliptic
from zerodb.storage import ZEOServer

DEFAULT_CONF_PATH = path.join(getcwd(), "conf", "server.zcml")

elliptic.register_auth()


@click.command()
@click.option("--confpath", default=DEFAULT_CONF_PATH, help="Path to config file")
def run(confpath):
    ZEOServer.run(["-C", confpath])


if __name__ == "__main__":

    # Simplest possible way to launch stunnel
    STUNNEL_CONF_PATH = path.join(getcwd(), "conf", "stunnel-server.conf")
    if path.exists(STUNNEL_CONF_PATH):
        from pystunnel import Stunnel
        stunnel = Stunnel(STUNNEL_CONF_PATH)
        rc = stunnel.start()
        print("stunnel started with rc %d" % rc)
        import atexit
        atexit.register(stunnel.stop)

    run()
