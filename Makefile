DOCKER_NAME = netopeer2-integration-test-env
DOCKER_RUN = docker run -it --rm -v $(shell pwd):/local -v $(shell pwd)/build/log:/var/log -w /local/tests -e LC_ALL=C.UTF-8 -e LANG=C.UTF-8 $(DOCKER_NAME)


.PHONY: test build

test: build/docker_built
	$(DOCKER_RUN) py.test -vvl $(PYTEST_ARGS)

format: build/docker_built
	$(DOCKER_RUN) black .

build: build/docker_built

build/docker_built: Dockerfile repo $(shell find repo -type f) $(shell find yang -type f) $(shell find support -type f) $(shell find test-service -type f)
	mkdir -p build/log/supervisor
	docker build -t $(DOCKER_NAME) .
	touch $@

repo:
	mkdir -p repo
	cd repo && \
	    git clone -b devel https://github.com/CESNET/libyang.git && \
	    git clone -b devel https://github.com/CESNET/libnetconf2.git && \
	    git clone -b devel https://github.com/sysrepo/sysrepo.git && \
	    git clone -b devel-server https://github.com/CESNET/Netopeer2.git
