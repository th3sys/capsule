#!/bin/sh
echo 'starting vnc'
/capsule/vnc.sh start
echo 'starting gateway'
supervisord -c /capsule/supervisord.conf
sleep 120
echo 'starting ibmarketdata'
python3 /capsule/ibmarketdata.py --host "127.0.0.1" --port 4002 --clientId 0 --real False --hist True
#echo 'done'
#ps -aef | grep Xtightvnc
#tail -f /capsule/sim/gw/ibgateway.log

#sleep 1200