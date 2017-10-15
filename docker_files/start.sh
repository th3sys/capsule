#!/bin/sh
echo 'starting vnc'
/capsule/vnc.sh start
echo 'starting gateway'
supervisord -c /capsule/supervisord.conf
sleep 5
echo 'done'
ps -aef | grep Xtightvnc
tail -f /capsule/sim/gw/ibgateway.log