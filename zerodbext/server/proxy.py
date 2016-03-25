#!/usr/bin/env python2

"""
Simple script to run proxy server.
You can specify socket name (can be UNIX or TCP socket).
"""

import click
from os import getcwd, path
from zerodb.storage import ZEOProxy

DEFAULT_CONF_PATH = path.join(getcwd(), "conf", "proxy.zcml")


@click.command()
@click.option("--confpath", default=DEFAULT_CONF_PATH, help="Path to config file")
def run(confpath):
    ZEOProxy.run(["-C", confpath])


if __name__ == "__main__":
    run()
