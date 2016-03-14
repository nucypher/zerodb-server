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
    run()
