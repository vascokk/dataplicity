#!/bin/bash

write_init() {
    cat >/etc/init.d/dataplicity-start <<EOL
#! /bin/sh

### BEGIN INIT INFO
# Provides:          dataplicity
# Required-Start:    \$local_fs \$network \$named \$time \$syslog
# Required-Stop:     \$local_fs \$network \$named \$time \$syslog
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
# Description:       dataplicity run script
### END INIT INFO

PATH=/bin:/usr/bin:/usr/local/bin:/sbin:/usr/sbin
LINES=24
COLUMNS=80
SHELL=/bin/bash
test -x /usr/local/bin/dataplicity || exit 0
umask 022
. /lib/lsb/init-functions

RUNAS=root

PIDFILE=/var/run/dataplicity.pid
LOGFILE=/var/log/dataplicity.log

start() {
  log_daemon_msg "Starting dataplicity..." "dataplicity" || true
  if start-stop-daemon --start --quiet --oknodo --pidfile \$PIDFILE --exec /usr/local/bin/dataplicity -- -c /opt/dataplicity/dataplicity.conf d; then
    log_end_msg 0 || true
  else
    log_end_msg 1 || true
  fi
}

stop() {
  log_daemon_msg "Stopping dataplicity..." "dataplicity" || true
  if start-stop-daemon --stop --quiet --oknodo --pidfile \$PIDFILE; then
    log_end_msg 0 || true
  else
    log_end_msg 1 || true
  fi
}

uninstall() {
  echo -n "Are you really sure you want to uninstall this service? That cannot be undone. [yes|No] "
  local SURE
  read SURE
  if [ "\$SURE" = "yes" ]; then
    stop
    rm -f "\$PIDFILE"
    echo "Notice: log file is not be removed: '\$LOGFILE'" >&2
    update-rc.d -f dataplicity-start remove
    rm -fv "\$0"
  fi
}

case "\$1" in
  start)
    start
    ;;
  stop)
    stop
    ;;
  uninstall)
    uninstall
    ;;
  restart)
    stop
    start
    ;;
  *)
    echo "Usage: \$0 {start|stop|restart|uninstall}"
esac
EOL

    chmod +x /etc/init.d/dataplicity-start
}

has_pip() {
    command -v pip >/dev/null 2>&1 || {
        return 1
    }
    return 0
}

check_dep() {
    command -v $1 >/dev/null 2>&1 || {
        echo >&2 "$1 is required. Please install and try again. Aborting"
        exit 1
    }
    return 0
}

install_commands() {
    # do stuff
    echo "Installing Dataplicity client...";
    mkdir -p /etc/dataplicity/
    mkdir -p /opt/dataplicity/

    pip install picamera
    pip install docutils

    if $(raspistill -o cam.jpg 2>null); then
        rm ./cam.jpg
    else
        echo "Warning: Your Pi Camera is disabled."
        echo "You can continue without camera functionality and enable it"
        echo "at any time by typing \"raspi-config\" at the shell prompt."
    fi

    if [ "$2" = "--dev" ]; then
        mkdir -p /opt/dataplicity/src/
        cd /opt/dataplicity/src/
        git clone https://github.com/wildfoundry/dataplicity.git
        cd /opt/dataplicity/src/dataplicity/
        python setup.py install
    else
        pip install -U dataplicity
    fi

    echo "Registering your device";
    dataplicity init --server https://api.dataplicity.com --system rpi --force --usercode $1
    dataplicity handoff --usercode $1
    cd /opt/dataplicity/
    dataplicity registersamplers

    write_init
    update-rc.d dataplicity-start defaults

    echo "Running samplers and syncing..."
    service dataplicity-start start
}

install() {
    apt-get install -y python-setuptools
    apt-get install -y python-dev

    if has_pip; then
        install_commands $1 $2
    else
        easy_install pip
        install_commands $1 $2
    fi

}

install $0 $1


