DOCKER_NAME = netopeer2-integration-test-env

.PHONY: test build

test build: build/docker_built
	@echo Running $@

build/docker_built: Dockerfile repo $(shell find repo -type f) $(shell find yang -type f)
	mkdir -p build
	docker build -t $(DOCKER_NAME) .
	touch $@

repo:
	mkdir -p repo
	cd repo && \
	    git clone -b devel https://github.com/CESNET/libyang.git && \
	    git clone -b devel https://github.com/CESNET/libnetconf2.git && \
	    git clone -b devel https://github.com/sysrepo/sysrepo.git && \
	    git clone -b devel-server https://github.com/CESNET/Netopeer2.git
