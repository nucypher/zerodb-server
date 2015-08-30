#!/bin/bash

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
