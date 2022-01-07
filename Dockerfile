FROM artifactory.adtran.com/docker/mosaic-os-service-kit-ubuntu18:latest
ARG DEBIAN_FRONTEND=noninteractive
ENV TZ=Europe/Berlin

# Setup build and runtime deps
RUN \
	apt-get update --fix-missing && apt-get install -y \
	acl \
	build-essential \
	ca-certificates \
	clang-format \
	cmake \
	curl \
	dos2unix \
	gdb \
	git \
	libavl-dev \
	libcmocka-dev \
	libcurl4-openssl-dev \
	libev-dev \
	libpcre2-dev \
	libpcre3-dev \
	libprotobuf-c-dev \
	libssl-dev \
	libz-dev \
	openssh-server \
	pcre2-utils \
	pkg-config \
	protobuf-c-compiler \
	python-dev \
	python3-pip \
#	python3-setuptools \
	rapidjson-dev \
	rsyslog \
	sudo \
	supervisor \
	swig \
	valgrind \
	vim && \
	update-ca-certificates


RUN \
	eval 'curl -o /tmp/rustup https://sh.rustup.rs' && \
	eval 'dos2unix /tmp/rustup' && \
	eval 'chmod a+x /tmp/rustup' && \
	/tmp/rustup -y && \
	eval 'cat /root/.cargo/env' && \
	eval 'export PATH=$PATH:/root/.cargo/bin' && \
	eval 'rustc --version'

RUN pip3 install setuptools-rust && \
    eval 'export PATH=$PATH:/root/.cargo/bin' && \
    pip3 install \
    ncclient \
    black==18.6b4 \
    pytest==3.6.3 \
    PyYAML==3.13 \
    requests==2.19.1 \
    pyasn1-modules==0.2.2

RUN pip3 install -e git+https://github.com/paramiko/paramiko/#egg=paramiko

# Build pistache, a REST toolkit for C++ used for the test_service.
# This project currently has no release tags, and POST requests fail
# beginning in pistache@496a2d1, so reset to the commit just prior to that.
RUN cd /tmp && \
    git clone --recursive https://github.com/oktal/pistache.git && \
    cd pistache && \
    git reset --hard c613852 && \
    mkdir build && \
    cd build && \
    cmake -DCMAKE_INSTALL_PREFIX=/usr .. && \
    make -j4 && \
    make install

RUN mkdir -p /tmp/repo && cd /tmp/repo && \
    git clone https://git.libssh.org/projects/libssh.git libssh && \
    cd libssh && mkdir build && cd build && \
    cmake -DCMAKE_INSTALL_PREFIX=/usr .. && \
    make && \
    make install && \
    ldconfig

# Build the stack
COPY repo/libyang /tmp/repo/libyang
RUN cd /tmp/repo/libyang && \
    mkdir build && cd build && \
    cmake -DCMAKE_INSTALL_PREFIX=/usr .. && \
    make -j4 && \
    make install && \
    ldconfig

COPY repo/libnetconf2 /tmp/repo/libnetconf2
RUN cd /tmp/repo/libnetconf2 && \
    mkdir build && cd build && \
    cmake -DCMAKE_INSTALL_PREFIX=/usr .. && \
    make -j4 && \
    make install && \
    ldconfig

COPY repo/sysrepo /tmp/repo/sysrepo
RUN cd /tmp/repo/sysrepo && \
    mkdir build && cd build && \
    cmake -DCMAKE_INSTALL_PREFIX=/usr .. && \
    make -j4 && \
    make install && \
    ldconfig

COPY repo/Netopeer2 /tmp/repo/Netopeer2
RUN cd /tmp/repo/Netopeer2/ && \
    mkdir build && cd build && \
    cmake -DCMAKE_INSTALL_PREFIX=/usr .. && \
    make -j4 && \
    make install && \
    ldconfig

COPY yang /tmp/yang
RUN cd /tmp/yang && python3 install.py

COPY test-service /tmp/test-service
RUN cd /tmp/test-service && \
    cmake -DCMAKE_INSTALL_PREFIX=/usr -DCMAKE_BUILD_TYPE=Debug . && \
    make -j4 && \
    make install

# add netconf user
RUN adduser --system netconf && \
    echo "netconf:netconf" | chpasswd

COPY support/start-netopeer2-server /usr/bin/start-netopeer2-server
COPY support/start-test-service /usr/bin/start-test-service
COPY support/supervisord.conf /etc/supervisor/conf.d/netopeer2-stack.conf
COPY support/libssh_server_config /etc/ssh/libssh_server_config

ENV LC_ALL C.UTF-8
ENV LANG C.UTF-8
