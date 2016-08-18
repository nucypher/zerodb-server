#!/usr/bin/env python3

import click

import falcon
import json
import meinheld

import imp
import inspect
import logging
import os

import zerodb

version = '1.0'
DEFAULT_CONFIG = os.path.join(os.path.dirname(__file__), 'default_conf.py')
db = None
models = None


class RootResource:
    def on_get(self, req, resp):
        classes = [k for k, v in models.__dict__.items()
                   if inspect.isclass(v) and
                   issubclass(v, zerodb.models.Model) and
                   v is not zerodb.models.Model]
        links = [{'href': '/' + c, 'rel': 'list', 'method': 'GET'}
                 for c in classes]
        resp.body = json.dumps(links)


api = falcon.API()
api.add_route('/', RootResource())


@click.command()
@click.option(
        "--config", default=DEFAULT_CONFIG, help="Path to config file")
def run(config):
    global db
    global models

    if config == DEFAULT_CONFIG:
        logging.warn('Using default config file. It is only an example!')
    conf = imp.load_source('config', config)
    models = imp.load_source('models', conf.models)

    # Connecting to zerodb
    db = zerodb.DB(
            conf.zerodb_sock,
            username=getattr(conf, 'username', None),
            password=getattr(conf, 'password', None),
            server_cert=getattr(conf, 'server_cert', None),
            cert_file=getattr(conf, 'client_cert', None),
            key_file=getattr(conf, 'client_key', None),
            wait_timeout=getattr(conf, 'wait_timeout', 10))

    meinheld.set_access_logger(None)
    meinheld.server.listen(conf.api_sock)
    print('Running API server at %s:%s' % conf.api_sock)
    meinheld.server.run(api)
    # TODO gunicorn

# json.dumps(obj.__dict__, ensure_ascii=False) - fast!


if __name__ == "__main__":
    run()
