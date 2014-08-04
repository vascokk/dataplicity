#!/bin/bash

has_pip() {
    command -v pip >/dev/null 2>&1 || {
        return 1
    }
    return 0
}

has_easy() {
    command -v easy_install >/dev/null 2>&1 || {
        return 1
    }
    return 0
}

install_commands() {
    # do stuff
    echo "Installing Dataplicity client...";
    mkdir -p /etc/dataplicity/
    mkdir -p /opt/dataplicity/

    if [ "$2" = "--dev" ]; then
        mkdir /opt/dataplicity/src/
        cd /opt/dataplicity/src/
        git clone https://github.com/wildfoundry/dataplicity.git
        cd /opt/dataplicity/src/dataplicity/
        python setup.py install
    else
        pip install dataplicity
    fi

    echo "Registering your device";
    dataplicity init --server https://api.dev.dataplicity.com --rpi --force --usercode $1
    dataplicity handoff --usercode $1
    cd /opt/dataplicity/
    dataplicity registersamplers

    echo "Running samplers and syncing..."
    dataplicity run
}

install() {
    if has_easy; then
        if has_pip; then
            install_commands $1 $2
        else
            easy_install pip
            install_commands $1 $2
        fi
    else
        echo >&2 "easy_install is required. Please install Python setup tools and try again. Aborting";
        exit 1
    fi
}

install $0 $1


