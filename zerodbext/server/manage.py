#!/usr/bin/env python3

"""
Management console
"""

import binascii
import click
import logging
import sys

import os.path

import six
from IPython import embed
from functools import update_wrapper

import ZODB.FileStorage

from zerodb import DB
from zerodb.permissions import base
from zerodbext.server.cert import generate_cert

logging.basicConfig()

_username = None
_passphrase = None
_sock = None
_server_certificate = None
_server_key = None
_user_certificate = None

ZEO_TEMPLATE = """<zeo>
  address {sock}
  <ssl>
    certificate {certificate}
    key {key}
    authenticate DYNAMIC
  </ssl>
</zeo>

<filestorage>
  path {dbfile}
  pack-gc false
</filestorage>"""


@click.group()
def cli():
    pass


# XXX make this more convenient, e.g.
# Generate server certificate [Y/n] etc
def _auth_options(f, confirm_passphrase=True):
    """Decorator to enable username, passphrase and sock options to command"""
    @click.option(
        "--server-certificate", prompt="Server certificate",
        type=click.STRING, default="",
        help="Server certificate file path (.pem)")
    @click.option(
        "--server-key", prompt="Server key",
        type=click.STRING, default="",
        help="Server certificate key file path (.pem)")
    @click.option(
            "--username", prompt="Username", default="root", type=click.STRING,
            help="Admin username")
    @click.option(
            "--passphrase", prompt="Passphrase", hide_input=True,
            confirmation_prompt=confirm_passphrase, type=click.STRING,
            default="", help="Admin passphrase")
    @click.option(
            "--sock", prompt="Sock", default="localhost:8001",
            type=click.STRING, help="Storage server socket (TCP or UNIX)")
    @click.option(
        "--user-certificate", prompt="User certificate",
        type=click.STRING, default="",
        help="User certificate file path (.pem)")
    @click.pass_context
    def auth_func(ctx, server_certificate, server_key,
                  username, passphrase, sock, user_certificate,
                  *args, **kw):
        global _username
        global _passphrase
        global _sock
        global _server_certificate
        global _server_key
        global _user_certificate

        _username = username
        _passphrase = passphrase or None
        _server_certificate = server_certificate or None
        _server_key = server_key or None
        _user_certificate = user_certificate or None

        if sock.startswith("/"):
            _sock = sock
        else:
            sock = sock.split(":")
            _sock = (str(sock[0]), int(sock[1]))
        ctx.invoke(f, *args, **kw)
    return update_wrapper(auth_func, f)


def signup_options(f):
    return _auth_options(f, confirm_passphrase=True)


def auth_options(f):
    return _auth_options(f, confirm_passphrase=False)


@cli.command()
@auth_options
def console():
    """
    Console for managing users (add, remove, change password)
    """

    # XXX redo all of these!!
    def useradd(username, pubkey):
        storage.add_user(username, binascii.unhexlify(pubkey))

    def userdel(username):
        storage.del_user(username)

    def chkey(username, pubkey):
        storage.change_key(username, binascii.unhexlify(pubkey))

    banner = "\n".join([
            "Usage:",
            "========",
            "useradd(username, pubkey) - add user",
            "userdel(username) - remove user",
            "chkey(username, pubkey) - change pubkey",
            "get_pubkey(username, password) - get public key from passphrase",
            "exit() or ^D - exit"])

    db = DB(_sock, username=_username, password=_passphrase)
    storage = db._storage

    sys.path.append(".")

    embed(banner1=banner)


@cli.command()
@click.option("--path", default=None, type=click.STRING,
              help="Path to db and configs")
@click.option("--absolute-path/--no-absolute-path", default=False,
              help="Use absolute paths in configs")
@signup_options
def init_db(path, absolute_path):
    """
    Initialize database if doesn't exist.
    Creates conf/ directory with config files and db/ with database files
    """
    global _server_key
    global _server_certificate
    global _user_certificate

    if path:
        if not os.path.exists(path):
            raise IOError("Path provided doesn't exist")
    else:
        path = os.getcwd()

    if absolute_path:
        dbfile_path = os.path.join(path, "db", "db.fs")
    else:
        dbfile_path = os.path.join("db", "db.fs")

    conf_dir = os.path.join(path, "conf")
    db_dir = os.path.join(path, "db")
    server_conf = os.path.join(conf_dir, "server.conf")

    if os.path.exists(server_conf):
        raise IOError("Config files already exist, remove them or edit")

    if not os.path.exists(conf_dir):
        os.mkdir(conf_dir)
    if not os.path.exists(db_dir):
        os.mkdir(db_dir)

    if not _server_key:
        key_pem, cert_pem = generate_cert()
        _server_key = os.path.join(conf_dir, "server_key.pem")
        _server_certificate = os.path.join(conf_dir, "server.pem")

        with open(_server_key, "w") as f:
            f.write(key_pem)

        with open(_server_certificate, "w") as f:
            f.write(cert_pem)

    server_content = ZEO_TEMPLATE.format(
        sock=_sock
        if isinstance(_sock, six.string_types) else "{0}:{1}".format(*_sock),
        dbfile=dbfile_path,
        certificate=_server_certificate,
        key=_server_key,
        )

    with open(server_conf, "w") as f:
        f.write(server_content)

    if not _user_certificate and not _passphrase:
        _user_certificate = os.path.join(conf_dir, "user.pem")
        _user_key = os.path.join(conf_dir, "user_key.pem")
        key_pem, cert_pem = generate_cert()

        with open(_user_key, "w") as f:
            f.write(key_pem)

        with open(_user_certificate, "w") as f:
            f.write(cert_pem)

    if _user_certificate:
        with open(_user_certificate) as f:
            pem_data = f.read()
    else:
        pem_data = None

    base.init_db(ZODB.FileStorage.FileStorage(dbfile_path),
                 uname=_username, password=_passphrase,
                 pem_data=pem_data)

    click.echo("Config files created, you can start zerodb-server")


@cli.command()
def clear():
    """
    Remove all database files (including auth db)
    """
    for f in os.listdir("db"):
        if f.startswith("db.fs"):
            os.remove(os.path.join("db", f))
    for f in os.listdir("conf"):
        if f.startswith("authdb.db"):
            os.remove(os.path.join("conf", f))

    click.echo("Database removed")


if __name__ == "__main__":
    cli()
