#!/bin/sh
export DISPLAY=:1
ROOTDIR=$( cd "$( dirname "$0" )" && pwd )
INSTANCE=$2
WORKINGDIR=$ROOTDIR/$INSTANCE
JAVA_HOME=/capsule/jdk1.8.0_05
PATH=$JAVA_HOME/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
JAVA=$JAVA_HOME/bin/java
COMMAND="$JAVA -cp jts.jar:total.2013.jar:IBController.jar ibcontroller.IBGatewayController IBController.ini"
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
       stop
       echo "Starting gateway $INSTANCE in $WORKINGDIR with pid: $$\n" >> $LOGFILE;
       echo $$ > $PIDFILE;
       cd $WORKINGDIR;
       exec $COMMAND 1>>$LOGFILE 2>&1
}

case $1 in
     start)
       /capsule/vnc.sh start
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