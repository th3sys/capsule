FROM ubuntu:14.04

# Install dependencies
RUN apt-get update -y

# create directories
RUN mkdir -p /capsule/gw

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
ENV JAVA_HOME       /usr/lib/jvm/java-8-oracle
RUN echo "oracle-java8-installer shared/accepted-oracle-license-v1-1 select true" | debconf-set-selections
RUN echo "deb http://ppa.launchpad.net/webupd8team/java/ubuntu xenial main" > /etc/apt/sources.list.d/webupd8team-java-trusty.list
RUN apt-key adv --keyserver keyserver.ubuntu.com --recv-keys EEA14886
RUN apt-get update && \
   apt-get install -y --no-install-recommends oracle-java8-installer && \
   apt-get clean all

# Install IB
RUN cd /capsule
RUN wget https://github.com/ib-controller/ib-controller/releases/download/2.11.0/IBControllerV2-11-0.zip
RUN wget https://download2.interactivebrokers.com/download/unixmacosx_latest.jar
RUN jar xf unixmacosx_latest.jar
RUN cp IBJts/* /capsule/gw
RUN rm -rf IBJts
RUN apt-get install -y unzip
RUN unzip IBControllerV2-11-0.zip -d /capsule/gw
ADD docker_files/IBController.ini /capsule/gw/IBController.ini
ADD docker_files/gw.sh /capsule/gw/gw.sh
RUN chmod +x /capsule/gw/gw.sh



EXPOSE 4001
ENTRYPOINT ["/capsule/gw/gw.sh", "start", "gw", "-D", "FOREGROUND"]