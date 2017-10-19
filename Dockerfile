FROM ubuntu:14.04

# Install dependencies
RUN apt-get update -y
RUN apt-get install -y supervisor
RUN apt-get install -y python3-pip
RUN apt-get install -y wget

# create directories
RUN mkdir -p /capsule/sim/gw

# Install tightvnc
ENV DEBIAN_FRONTEND noninteractive
ENV USER root
RUN apt-get autoremove
RUN apt-get install -y --no-install-recommends ubuntu-desktop
RUN apt-get install -y --no-install-recommends tightvncserver xfce4 xfce4-goodies
# apt-get install -y gnome-panel gnome-settings-daemon metacity nautilus gnome-terminal
RUN mkdir /root/.vnc && echo "password" > /root/.vnc/passwd && chmod 600 /root/.vnc/passwd
ADD docker_files/xstartup /root/.vnc/xstartup

# Vnc startup script
ADD docker_files/vnc.sh /capsule/vnc.sh
RUN chmod +x /capsule/vnc.sh


# Install Oracle's JDK
RUN apt-get install -y --no-install-recommends software-properties-common
RUN add-apt-repository -y ppa:openjdk-r/ppa
RUN apt-get update
RUN apt-get install -y openjdk-8-jdk
RUN apt-get install -y openjdk-8-jre
RUN update-alternatives --config java
RUN update-alternatives --config javac

# Install IB
RUN cd /capsule
RUN wget https://github.com/ib-controller/ib-controller/releases/download/2.11.0/IBControllerV2-11-0.zip
RUN wget https://download2.interactivebrokers.com/download/unixmacosx_latest.jar
RUN jar xf unixmacosx_latest.jar
RUN cp IBJts/* /capsule/sim/gw
RUN rm -rf IBJts
RUN apt-get install -y unzip
RUN unzip IBControllerV2-11-0.zip -d /capsule/sim/gw
ADD docker_files/IBController.ini /capsule/sim/gw/IBController.ini
ADD docker_files/gw.sh /capsule/gw.sh

# Python
RUN cd /capsule
RUN wget https://raw.githubusercontent.com/th3sys/capsule/master/ibmarketdata.py -P /capsule
#ADD ibmarketdata.py /capsule/ibmarketdata.py
RUN pip3 install boto3
ADD docker_files/credentials.aws /root/.aws/credentials
ADD docker_files/config.aws /root/.aws/config
RUN mkdir /capsule/api
RUN mkdir /capsule/ibapi
RUN wget http://interactivebrokers.github.io/downloads/twsapi_macunix.973.05.zip
RUN unzip -o twsapi_macunix.973.05.zip -d /capsule/api
RUN cp -r /capsule/api/IBJts/source/pythonclient/ibapi/* /capsule/ibapi

# Scripts
RUN chmod +x /capsule/gw.sh
ADD docker_files/supervisord.conf /capsule/supervisord.conf
ADD docker_files/start.sh /capsule/start.sh
RUN chmod +x /capsule/start.sh

EXPOSE 4001
ENTRYPOINT ["/capsule/start.sh", "-D", "FOREGROUND"]