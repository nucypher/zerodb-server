#!/usr/bin/env python3

import click

import codecs
import falcon
import json
import meinheld
import transaction

import imp
import inspect
import logging
import os

import zerodb

version = '1.0'
DEFAULT_CONFIG = os.path.join(os.path.dirname(__file__), 'default_conf.py')
reader = codecs.getreader('utf-8')
db = None
models = None


def exception_handler(e, req, resp, params):
    resp.body = json.dumps({
        'ok': 0,
        'message': str(e),
        'error_type': e.__class__.__name__
        })
    resp.status = falcon.HTTP_500


class JSONResource:
    on_get_json = None
    on_post_json = None
    requires_data = False

    def on_get(self, req, resp, **kw):
        if self.on_get_json is None:
            raise falcon.HTTPBadRequest(
                'Bad request', 'GET method is not allowed')
        else:
            if self.requires_data:
                stream = json.load(reader(req.stream))
            else:
                stream = None
            out = self.on_get_json(stream, resp, *kw)
            out.update({'ok': 1})
            resp.body = json.dumps(out)

    def on_post(self, req, resp, **kw):
        if self.on_post_json is None:
            raise falcon.HTTPBadRequest(
                'Bad request', 'POST method is not allowed')
        else:
            if self.requires_data:
                stream = json.load(reader(req.stream))
            else:
                stream = None
            out = self.on_post_json(stream, resp, **kw)
            out.update({'ok': 1})
            resp.body = json.dumps(out)


class RootResource(JSONResource):
    requires_data = False

    def on_get_json(self, req, resp):
        classes = [k for k, v in models.__dict__.items()
                   if inspect.isclass(v) and
                   issubclass(v, zerodb.models.Model) and
                   v is not zerodb.models.Model]
        return {'links': [{
                    'href': '/' + c,
                    'rel': 'list',
                    'method': 'GET'}
                 for c in classes]}


class InsertResource(JSONResource):
    requires_data = True

    def on_post_json(self, stream, resp, name):
        model = getattr(models, name)
        if stream:
            data = stream.get('docs', [])
        else:
            data = []
        objs = [model(**row) for row in data]
        with transaction.manager:
            oids = [{'$oid': db.add(o)} for o in objs]
        return {'oids': oids}


api = falcon.API()
api.add_route('/', RootResource())
api.add_route('/{name}/_insert', InsertResource())
api.add_error_handler(Exception, exception_handler)


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
