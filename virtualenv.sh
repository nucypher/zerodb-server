#!/bin/bash

if [ ! -d ".venv" ]
then
    virtualenv -p python2 .venv
    source .venv/bin/activate
    python setup.py develop
    ln -s .venv/bin/activate .
else
    echo "All done already"
    echo "  source activate -- activate virtual environment"
    echo "  deactivate      -- leave virtual environment"
fi
