#!/bin/sh
cd /capsule/sim/gw
export DISPLAY=:1
ROOTDIR=$( cd "$( dirname "$0" )" && pwd )
INSTANCE=$2
WORKINGDIR=$ROOTDIR/$INSTANCE
JAVA_HOME=/usr
PATH=$JAVA_HOME/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
JAVA=$JAVA_HOME/bin/java
COMMAND="$JAVA -cp jts4launch-963.jar:locales.jar:log4j-api-2.5.jar:log4j-core-2.5.jar:total-2015c.jar:twslaunch-963.jar:IBController.jar ibcontroller.IBGatewayController IBController.ini"
PIDFILE=$WORKINGDIR/ibgateway.pid
LOGFILE=$WORKINGDIR/ibgateway.log

stop()
{
   if kill -0 `cat $PIDFILE` >/dev/null 2>&1; then
       echo "Stopping gateway $INSTANCE with pid: `cat $PIDFILE`\n" >> $LOGFILE;
       kill -9 `cat $PIDFILE`
   fi
}

restart()
{
       # stop
       echo "Starting gateway $INSTANCE in $WORKINGDIR with pid: $$\n" >> $LOGFILE;
       echo $$ > $PIDFILE;
       cd $WORKINGDIR;
       exec $COMMAND 1>>$LOGFILE 2>&1
}

case $1 in
     start)
       restart
       ;;
     restart)
       restart
       ;;
     stop)
       stop
       ;;
     *)
       echo "usage: gw.sh {start|stop|restart} <instance>" ;;
esac
exit 0