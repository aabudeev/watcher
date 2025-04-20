#!/bin/bash

N='\e[0m'
G='\e[1;32m'
B='\e[34m'

usage () {
    printf "For help:${B}                   ./`basename ${0}`${G} help${N}\n"
    printf "For run:${B}                    ./`basename ${0}`${G} run${N}\n"
    printf "For install:${B}                ./`basename ${0}`${G} install${N}\n"
    printf "For uninstall:${B}              ./`basename ${0}`${G} uninstall${N}\n"
    printf "For generate crypto key:${B}    ./`basename ${0}`${G} gen${N}\n"
}

install () {
    if [[ ! -d venv ]]; then
        python3 -m venv venv
    fi

    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    pip freeze
}

uninstall () {
    source venv/bin/activate
    pip uninstall -r requirements.txt -y
    rm -rvf venv watcher.lo* __pycache__
}

run () {
    source venv/bin/activate
    ./watcher.py
}

gen () {
    source venv/bin/activate
    ./watcher_gen.py
}

while [[ ${#} -gt 0 ]]; do case ${1} in
    help)       usage;;
    run)        run;;
    install)    install;;
    uninstall)  uninstall;;
    gen)        gen;;
esac; shift; done