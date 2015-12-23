#!/usr/bin/env python2

import click
from Crypto import Random
from zerodb import api


@click.command()
@click.option("--api-host", default="localhost", help="Host for API")
@click.option("--api-port", default=17234, help="Port for API", type=click.IntRange(0, 65535))
@click.option("--zerodb-host", default="localhost", help="Host where ZeroDB server is running")
@click.option("--zerodb-port", default=8001, help="Port where ZeroDB server is running", type=click.IntRange(0, 65535))
@click.option("--models", default="models.py", help="File with models")
@click.option("--session-key", help="Session key which should be random")
def run(api_host, api_port, zerodb_host, zerodb_port, models, session_key):
    if not session_key:
        session_key = Random.get_random_bytes(24)
    api.run(data_models=models, host=api_host, port=api_port, secret_key=session_key, debug=False, zeo_socket=(zerodb_host, zerodb_port))


if __name__ == "__main__":
    run()
