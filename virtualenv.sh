#!/bin/bash

if [ ! -e "api_server/cert.pem" ]
then
  echo "Generating new self-signed SSL certificates"
  echo "Please complete the following..."
  openssl ecparam -genkey -name secp256k1 -out api_server/key.pem
  openssl req -new -key api_server/key.pem -out api_server/cert.pem -x509 -days 1000
  echo "Self-signed SSL certificates generated"
fi

if [ ! -d ".venv" ]
then
    virtualenv .venv
    source .venv/bin/activate
    pip install IPython
    pip install loremipsum
    pip install names
    pushd dist
    easy_install `ls -1 | tail -n 1`
    popd
    ln -s .venv/bin/activate .
else
    echo "All done already"
    echo "  source activate -- activate virtual environment"
    echo "  deactivate      -- leave virtual environment"
fi
