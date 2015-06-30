#!/bin/bash

if [ ! -d ".venv" ]
then
    virtualenv .venv
    source .venv/bin/activate
    pip install IPython
    pip install loremipsum
    pip install names
    pushd dist
    easy_install zerodb-0.91.1-py2.7.egg
    popd
    ln -s .venv/bin/activate .
else
    echo "All done already"
    echo "  source activate -- activate virtual environment"
    echo "  deactivate      -- leave virtual environment"
fi
