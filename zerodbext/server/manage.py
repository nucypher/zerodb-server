#!/usr/bin/env python2

"""
Management console
"""

import binascii
import click
import logging

import os.path

import six
from IPython import embed
from functools import update_wrapper

from zerodb import DB
from zerodb.crypto import ecc
from zerodb.permissions import elliptic
from zerodb.storage import client_storage

logging.basicConfig()

_username = None
_passphrase = None
_sock = None
_realm = None
kdf = elliptic.Client.kdf

PERMISSIONS_TEMPLATE = """realm {realm}
auth_secp256k1_scrypt:{username}:{passphrase}"""

ZEO_TEMPLATE = """<zeo>
  address {sock}
  authentication-protocol auth_secp256k1_scrypt
  authentication-database {authdb}
  authentication-realm {realm}
</zeo>

<filestorage>
  path {dbfile}
  pack-gc false
</filestorage>"""


def get_pubkey(username, password):
    pub = ecc.private(
            str(password), (str(username), str(_realm)), kdf=kdf).get_pubkey()
    if six.PY2:
        return pub.encode("hex")
    else:
        return pub.hex()


@click.group()
def cli():
    pass


def _auth_options(f, confirm_passphrase=True):
    """Decorator to enable username, passphrase and sock options to command"""
    @click.option(
            "--username", prompt="Username", default="root", type=click.STRING,
            help="Admin username")
    @click.option(
            "--passphrase", prompt="Passphrase", hide_input=True,
            confirmation_prompt=confirm_passphrase, type=click.STRING,
            help="Admin passphrase or hex private key")
    @click.option(
            "--sock", prompt="Sock", default="localhost:8001",
            type=click.STRING, help="Storage server socket (TCP or UNIX)")
    @click.option("--realm", default="ZERO", type=click.STRING,
                  help="Authentication realm")
    @click.pass_context
    def auth_func(ctx, username, passphrase, sock, realm, *args, **kw):
        global _username
        global _passphrase
        global _sock
        global _realm

        _realm = str(realm)
        _username = str(username)
        _passphrase = str(passphrase)

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

    DB.auth_module.register_auth()
    DB._init_default_crypto(passphrase=_passphrase)

    storage = client_storage(
            _sock, username=_username, password=_passphrase, realm=_realm)
    embed(banner1=banner)


@cli.command()
@click.option("--path", default=None, type=click.STRING, help="Path to db and configs")
@click.option("--absolute-path/--no-absolute-path", default=False, help="Use absolute paths in configs")
@signup_options
def init_db(path, absolute_path):
    """
    Initialize database if doesn't exist.
    Creates conf/ directory with config files and db/ with database files
    """
    if path:
        if not os.path.exists(path):
            raise IOError("Path provided doesn't exist")
    else:
        path = os.getcwd()

    if absolute_path:
        authdb_path = os.path.join(path, "conf", "authdb.conf")
        dbfile_path = os.path.join(path, "db", "db.fs")
    else:
        authdb_path = os.path.join("conf", "authdb.conf")
        dbfile_path = os.path.join("db", "db.fs")

    conf_dir = os.path.join(path, "conf")
    db_dir = os.path.join(path, "db")
    authdb_conf = os.path.join(conf_dir, "authdb.conf")
    zcml_conf = os.path.join(conf_dir, "server.zcml")

    if os.path.exists(authdb_conf) or os.path.exists(zcml_conf):
        raise IOError("Config files already exist, remove them or edit")

    if not os.path.exists(conf_dir):
        os.mkdir(conf_dir)
    if not os.path.exists(db_dir):
        os.mkdir(db_dir)

    key = get_pubkey(_username, _passphrase)
    authdb_content = PERMISSIONS_TEMPLATE.format(
            username=_username,
            passphrase=key,
            realm=_realm)
    zcml_content = ZEO_TEMPLATE.format(
            sock=_sock if isinstance(_sock, six.string_types) else "{0}:{1}".format(*_sock),
            authdb=authdb_path,
            dbfile=dbfile_path,
            realm=_realm)

    with open(authdb_conf, "w") as f:
        f.write(authdb_content)

    with open(zcml_conf, "w") as f:
        f.write(zcml_content)

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
