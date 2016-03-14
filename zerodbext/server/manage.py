#!/usr/bin/env python2

"""
Management console
"""

import click
import logging
import subprocess

import os.path

import six
from IPython import embed
from functools import update_wrapper

from zerodb import DB
from zerodb.crypto import ecc
from zerodb.storage import client_storage
from zerodb.transform import init_crypto

logging.basicConfig()

_username = None
_passphrase = None
_sock = None

PERMISSIONS_TEMPLATE = """realm ZERO
{username}:{passphrase}"""

ZEO_TEMPLATE = """<zeo>
  address {sock}
  authentication-protocol ecc_auth
  authentication-database {authdb}
  authentication-realm ZERO
</zeo>

<filestorage>
  path {dbfile}
  pack-gc false
</filestorage>"""

STUNNEL_SERVER_TEMPLATE = """\
; stunnel config for ZeroDB server
; https://www.stunnel.org/static/stunnel.html

; PID file, path must be absolute
pid = {pidfile}

[zerodb-server]
; Listen on all interfaces
accept = {accept}
; Forward to ZeroDB server on localhost
connect = {connect}
; TLS server certificate and key files
cert = {certfile}
key = {keyfile}
"""

STUNNEL_CLIENT_TEMPLATE = """\
; stunnel config for ZeroDB client
; https://www.stunnel.org/static/stunnel.html

; PID file, path must be absolute
pid = {pidfile}

[zerodb-client]
; Operate in client mode
client = yes
; Listen on localhost
accept = {accept}
; Forward to remote ZeroDB server
connect = {connect}
; Authenticate against local copy
; of server certificate
CAfile = {certfile}
verify = 4
"""


@click.group()
def cli():
    pass


def _auth_options(f, confirm_passphrase=True):
    """Decorator to enable username, passphrase and sock options to command"""
    @click.option("--username", prompt="Username", default="root", type=click.STRING, help="Admin username")
    @click.option("--passphrase", prompt="Passphrase", hide_input=True, confirmation_prompt=confirm_passphrase, type=click.STRING, help="Admin passphrase or hex private key")
    @click.option("--sock", prompt="Sock", default="localhost:8001", type=click.STRING, help="Storage server socket (TCP or UNIX)")
    @click.pass_context
    def auth_func(ctx, username, passphrase, sock, *args, **kw):
        global _username
        global _passphrase
        global _sock

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

    def useradd(username, password):
        storage.add_user(username, password)

    def userdel(username):
        storage.del_user(username)

    def chpass(username, password):
        storage.change_key(username, password)

    banner = "\n".join([
            "Usage:",
            "========",
            "useradd(username, password) - add user",
            "userdel(username) - remove user",
            "chpass(username, password) - change passphrase",
            "exit() or ^D - exit"
            ])

    DB.auth_module.register_auth()
    DB.encrypter.register_class(default=True)
    init_crypto(passphrase=_passphrase)

    storage = client_storage(_sock,
            username=_username, password=_passphrase, realm="ZERO")
    embed(banner1=banner)


@cli.command()
@click.option("--path", default=None, type=click.STRING, help="Path to db and configs")
@click.option("--absolute-path/--no-absolute-path", default=False, help="Use absolute paths in configs")
@click.option("--stunnel-server", default=None, type=click.STRING, help="stunnel server address:port")
@click.option("--stunnel-client", default=None, type=click.STRING, help="stunnel client address:port")
@signup_options
def init_db(path, absolute_path, stunnel_server, stunnel_client):
    """
    Initialize database if doesn't exist.
    Creates conf/ directory with config files and db/ with database files
    """
    stunnel = stunnel_server is not None or stunnel_client is not None

    if path:
        if not os.path.exists(path):
            raise IOError("Path provided doesn't exist")
    else:
        path = os.getcwd()

    if absolute_path:
        authdb_path = os.path.join(path, "conf", "authdb.conf")
        dbfile_path = os.path.join(path, "db", "db.fs")
        certfile_path = os.path.join(path, "conf", "server.crt")
        keyfile_path = os.path.join(path, "conf", "server.key")
    else:
        authdb_path = os.path.join("conf", "authdb.conf")
        dbfile_path = os.path.join("db", "db.fs")
        certfile_path = os.path.join("conf", "server.crt")
        keyfile_path = os.path.join("conf", "server.key")

    conf_dir = os.path.join(path, "conf")
    db_dir = os.path.join(path, "db")
    var_dir = os.path.join(path, "var")
    authdb_conf = os.path.join(conf_dir, "authdb.conf")
    zcml_conf = os.path.join(conf_dir, "server.zcml")
    certfile = os.path.join(conf_dir, "server.crt")
    keyfile = os.path.join(conf_dir, "server.key")
    stunnel_server_conf = os.path.join(conf_dir, "stunnel-server.conf")
    stunnel_client_conf = os.path.join(conf_dir, "stunnel-client.conf")

    if os.path.exists(authdb_conf) or os.path.exists(zcml_conf):
        click.echo("Config files already exist, remove to recreate")

    if not os.path.exists(conf_dir):
        os.mkdir(conf_dir)
    if not os.path.exists(db_dir):
        os.mkdir(db_dir)

    if stunnel:
        if not os.path.exists(var_dir):
            os.mkdir(var_dir)

    key = ecc.private(_passphrase).get_pubkey()
    if six.PY2:
        key = key.encode('hex')
    else:
        key = key.hex()

    sock = _sock if isinstance(_sock, six.string_types) else "{0}:{1}".format(*_sock)
    server_accept = "9001"
    server_connect = "<server address>:9001"
    client_accept = sock

    if stunnel:
        if stunnel_server is not None:
            server_accept = stunnel_server.split(":")[1]
            server_connect = stunnel_server
        if stunnel_client is not None:
            client_accept = stunnel_client

    authdb_content = PERMISSIONS_TEMPLATE.format(
            username=_username,
            passphrase=key)

    zcml_content = ZEO_TEMPLATE.format(
            sock=sock,
            authdb=authdb_path,
            dbfile=dbfile_path)

    stunnel_server_content = STUNNEL_SERVER_TEMPLATE.format(
            pidfile=os.path.join(path, "var", "stunnel-server.pid"),
            accept=server_accept,
            connect=sock,
            certfile=certfile_path,
            keyfile=keyfile_path)

    stunnel_client_content = STUNNEL_CLIENT_TEMPLATE.format(
            pidfile="<"+os.path.join(os.sep, "path", "to", "stunnel-client.pid")+">",
            accept=client_accept,
            connect=server_connect,
            certfile="<"+os.path.join(os.sep, "path", "to", "server.crt")+">")

    if os.path.exists(authdb_conf):
        click.echo("Skipping " + authdb_conf)
    else:
        with open(authdb_conf, "w") as f:
            f.write(authdb_content)

    if os.path.exists(zcml_conf):
        click.echo("Skipping " + zcml_conf)
    else:
        with open(zcml_conf, "w") as f:
            f.write(zcml_content)

    if stunnel:
        if os.path.exists(stunnel_server_conf):
            click.echo("Skipping " + stunnel_server_conf)
        else:
            with open(stunnel_server_conf, "w") as f:
                f.write(stunnel_server_content)

        if os.path.exists(stunnel_client_conf):
            click.echo("Skipping " + stunnel_client_conf)
        else:
            with open(stunnel_client_conf, "w") as f:
                f.write(stunnel_client_content)

    if stunnel:
        if os.path.exists(keyfile):
            click.echo("Skipping " + keyfile)
        else:
            subprocess.call('umask 077; openssl ecparam -genkey -name secp256k1 -out "{0}"'.format(
                keyfile), shell=True)
            if os.path.exists(certfile):
                os.remove(certfile)

        if os.path.exists(certfile):
            click.echo("Skipping " + certfile)
        else:
            subprocess.call('openssl req -new -key "{0}" -out "{1}" -x509 -days 1000'.format(
                keyfile, certfile), shell=True)

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
