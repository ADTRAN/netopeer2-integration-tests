FROM ubuntu:18.04

# Setup build and runtime deps
RUN apt-get update && \
    apt-get install -y \
        git \
        cmake \
        build-essential \
        libssh-dev \
        libpcre3-dev \
        pkg-config \
        libavl-dev \
        libev-dev \
        libprotobuf-c-dev \
        protobuf-c-compiler \
        valgrind \
        sudo \
        libcmocka-dev \
        acl \
        python3-pip \
        supervisor \
        rsyslog \
        openssh-server
RUN pip3 install \
    ncclient==0.5.4 \
    black==18.6b4 \
    pytest==3.6.3 \
    PyYAML==3.13

# Build the stack
COPY repo/libyang /tmp/repo/libyang
RUN cd /tmp/repo/libyang && \
    cmake -DCMAKE_INSTALL_PREFIX=/usr -DENABLE_BUILD_TESTS=Off -DENABLE_VALGRIND_TESTS=Off . && \
    make -j4 && \
    make install

COPY repo/libnetconf2 /tmp/repo/libnetconf2
RUN cd /tmp/repo/libnetconf2 && \
    cmake -DCMAKE_INSTALL_PREFIX=/usr -DENABLE_BUILD_TESTS=Off -DENABLE_VALGRIND_TESTS=Off . && \
    make -j4 && \
    make install

COPY repo/sysrepo /tmp/repo/sysrepo
RUN cd /tmp/repo/sysrepo && \
    cmake -DCMAKE_INSTALL_PREFIX=/usr -DENABLE_TESTS=0 . && \
    make -j4 && \
    make install

COPY repo/Netopeer2 /tmp/repo/Netopeer2
RUN cd /tmp/repo/Netopeer2/server && \
    cmake -DCMAKE_INSTALL_PREFIX=/usr -DENABLE_BUILD_TESTS=Off -DENABLE_VALGRIND_TESTS=Off . && \
    make -j4 && \
    make install

COPY yang /tmp/yang
RUN cd /tmp/yang && python3 install.py

COPY test-service /tmp/test-service
RUN g++ -g -o /usr/bin/test-service /tmp/test-service/*.cpp -lsysrepo

COPY support/start-netopeer2-server /usr/bin/start-netopeer2-server
COPY support/start-test-service /usr/bin/start-test-service
COPY support/supervisord.conf /etc/supervisor/conf.d/netopeer2-stack.conf
