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
from itertools import chain

import zerodb
from zerodb.catalog.query import optimize
from zerodb.catalog import query_json as qj

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
            if self.requires_data and req.params:
                stream = req.params
            else:
                stream = None
            out = self.on_get_json(stream, resp, **kw) or {}
            out.update({'ok': 1})
            resp.body = json.dumps(out, ensure_ascii=False)

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
            resp.body = json.dumps(out, ensure_ascii=False)


class RootResource(JSONResource):
    requires_data = False

    def on_get_json(self, req, resp):
        classes = [k for k, v in models.__dict__.items()
                   if inspect.isclass(v) and
                   issubclass(v, zerodb.models.Model) and
                   v is not zerodb.models.Model]
        return {'links': list(chain(*[
            [
                {'href': '/%s/_insert' % c,
                 'rel': 'list',
                 'method': 'POST'},
                {'href': '/%s/_get' % c,
                 'rel': 'list',
                 'method': ['GET', 'POST']},
                {'href': '/%s/_find' % c,
                 'rel': 'list',
                 'method': ['GET', 'POST']},
                {'href': '/%s/_remove' % c,
                 'rel': 'list',
                 'method': ['GET', 'POST']}
            ]
            for c in classes]))}


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


class GetResource(JSONResource):
    requires_data = True

    def _run(self, stream, resp, name):
        model = getattr(models, name)
        _id = int(stream['_id'])

        try:
            obj = db[model][_id]
            obj._p_activate()
        finally:
            transaction.abort()
        return {'results': [obj.__dict__]}

    def on_get_json(self, stream, resp, name):
        return self._run(stream, resp, name)

    def on_post_json(self, stream, resp, name):
        return self._run(stream, resp, name)


class FindResource(JSONResource):
    requires_data = True

    def _run(self, stream, resp, name):
        model = getattr(models, name)
        criteria = stream['criteria']
        if isinstance(criteria, str):
            criteria = json.loads(criteria)

        if isinstance(criteria, dict) and (len(criteria) == 1) and "_id" in criteria:
            ids = [c["$oid"] for c in criteria["_id"]]
        else:
            ids = None
            criteria = optimize(qj.compile(criteria))

        skip = stream.get("skip")
        if skip:
            skip = int(skip)

        limit = stream.get("limit")
        if limit:
            limit = int(limit)

        sort = stream.get("sort")
        if sort:
            try:
                sort = json.loads(sort)
            except ValueError:
                if sort.startswith("-"):
                    sort_index = sort[1:].strip()
                    reverse = True
                else:
                    sort_index = sort
                    reverse = None
            if isinstance(sort, dict):
                assert len(sort) == 1  # Only one field at the moment
                sort_index, direction = sort.popitem()
                reverse = (direction >= 0)
            elif isinstance(sort, list):
                sort_index = sort[0]
                reverse = None
        else:
            sort_index = None
            reverse = None

        try:
            if ids:
                skip = skip or 0
                end = skip + limit if limit else None
                ids = ids[skip:end]
                result = db[model][ids]
            else:
                result = db[model].query(
                        criteria, skip=skip, limit=limit, sort_index=sort_index,
                        reverse=reverse)
            for obj in result:
                obj._p_activate()
        finally:
            transaction.abort()

        return {'results': [r.__dict__ for r in result], 'count': len(result)}

    def on_get_json(self, stream, resp, name):
        return self._run(stream, resp, name)

    def on_post_json(self, stream, resp, name):
        return self._run(stream, resp, name)


class RemoveResource(JSONResource):
    requires_data = True

    def _run(self, stream, resp, name):
        model = getattr(models, name)

        criteria = stream.get('criteria')
        ids = stream.get('_id')

        with transaction.manager:
            if criteria:
                if isinstance(criteria, str):
                    criteria = json.loads(criteria)

                if isinstance(criteria, dict) and (len(criteria) == 1) and "_id" in criteria:
                    ids = [c["$oid"] for c in criteria["_id"]]
                else:
                    ids = None
                    criteria = optimize(qj.compile(criteria))
                result = db[model].query(criteria)

            elif ids:
                ids = json.loads(ids)
                result = db[model][ids]

            else:
                raise AttributeError("Not enough arguments")

            count = db.remove(result)
            return {'ok': 1, 'count': count}

    def on_get_json(self, stream, resp, name):
        return self._run(stream, resp, name)

    def on_post_json(self, stream, resp, name):
        return self._run(stream, resp, name)


api = falcon.API()
api.add_route('/', RootResource())
api.add_route('/{name}/_insert', InsertResource())
api.add_route('/{name}/_get', GetResource())
api.add_route('/{name}/_find', FindResource())
api.add_route('/{name}/_remove', RemoveResource())


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

    if not conf.debug:
        api.add_error_handler(Exception, exception_handler)
        meinheld.set_access_logger(None)
    meinheld.server.listen(conf.api_sock)
    print('Running API server at %s:%s' % conf.api_sock)
    meinheld.server.run(api)
    # TODO gunicorn


if __name__ == "__main__":
    run()
