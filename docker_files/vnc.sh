#!/bin/sh

ROOTDIR=$( cd "$( dirname "$0" )" && pwd )
PATH=/sbin:/usr/sbin:/bin:/usr/bin
NAME="VNC"
PIDFILE=$ROOTDIR/vnc.pid
LOGFILE=$ROOTDIR/vnc.log
DISPN=1

stop()
{
    if kill -0 `cat $PIDFILE` >/dev/null 2>&1; then
        echo "Stopping $NAME with pid: `cat $PIDFILE`\n" >> $LOGFILE;
        kill -9 `cat $PIDFILE`
    fi
}

restart()
{
    exec > $LOGFILE 2>&1
    stop
    echo $$ > $PIDFILE;
    echo "Starting $NAME with pid: $$\n";
    export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
    export HOME=/root
    export USER=root
    export XAUTHORITY=/root/.Xauthority
    rm -f /tmp/.X$DISPN-lock
    rm -rf /tmp/.X11-unix
    exec /usr/bin/vncserver -geometry 1024x768 :$DISPN -fp /usr/share/fonts/X11/misc -localhost
}

case $1 in
    start)
        restart
    ;;
    stop)
        stop
    ;;
    *)
        echo "usage: vnc.sh {start|stop}" ;;
esac
exit 0