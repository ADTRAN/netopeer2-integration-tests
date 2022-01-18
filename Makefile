DOCKER_NAME := netopeer2-integration-test-env
CONT_NAME := netopeer2-test
INTEGRATION_TEST_DIR ?= $(shell pwd)
DOCKER_RUN := docker run -it --rm -v $(INTEGRATION_TEST_DIR):/local -v $(INTEGRATION_TEST_DIR)/log:/var/log -w /local/tests --privileged $(DOCKER_NAME)

PYTEST_ARGS ?= -x

WORKSPACE_DIR  := $(abspath ./repo)
libyang_GITHUB_URL := https://github.com/CESNET/libyang.git
sysrepo_GITHUB_URL := https://github.com/sysrepo/sysrepo.git
Netopeer2_GITHUB_URL := https://github.com/CESNET/Netopeer2.git
libnetconf2_GITHUB_URL := https://github.com/CESNET/libnetconf2.git
NC2_PKGS  := libyang libnetconf2 sysrepo Netopeer2
PKG_WORKSPACES := $(addprefix $(WORKSPACE_DIR)/,$(NC2_PKGS))


$(WORKSPACE_DIR):
	@mkdir -p $@

.PHONY: test-env
test-env: build/docker_built
	@mkdir -p log/supervisor

.PHONY: test
test: test-env
	@$(DOCKER_RUN) py.test -vvl $(PYTEST_ARGS) ; \
	_PYTEST_EXIT_CODE=$$? ; \
	$(DOCKER_RUN) chown -R $(shell id -u):$(shell id -g) /var/log ; \
	exit $$_PYTEST_EXIT_CODE

.PHONY: docker-shell
docker-shell: test-env
	@docker run -d --rm -v $(INTEGRATION_TEST_DIR):/local -v $(INTEGRATION_TEST_DIR)/log:/var/log -w /local/standalone-support --name $(CONT_NAME) --privileged $(DOCKER_NAME) tail -F -n0 /etc/hosts ; \
	docker exec -ti $(CONT_NAME) bash ; \
	$(DOCKER_RUN) chown -R $(shell id -u):$(shell id -g) /var/log ; \
	docker stop $(CONT_NAME)

.PHONY: format
format: build/docker_built
	$(DOCKER_RUN) black .
	$(DOCKER_RUN) /bin/sh -c 'find ../test-service \( -name "*.hpp" -o -name "*.cpp" \) | xargs clang-format -i'
	$(DOCKER_RUN) chown -R $(shell id -u):$(shell id -g) ../test-service

.PHONY: build
build: build/docker_built

#NO_TMP_IMGS = --force-rm

build/docker_built: Dockerfile $(PKG_WORKSPACES) $(shell find yang -type f) $(shell find support -type f) $(shell find test-service -type f)
	mkdir -p $(@D)
	docker build -t $(NO_TMP_IMGS) $(DOCKER_NAME) .
	touch $@

.PHONY: clean
clean:
	$(DOCKER_RUN) chown -R $(shell id -u):$(shell id -g) /var/log ;
	rm -rf log
	rm -rf build
	rm -rf repo

.PHONY: workspace
workspace: $(PKG_WORKSPACES);

.PRECIOUS: $(WORKSPACE_DIR)/%
$(WORKSPACE_DIR)/% : | $(WORKSPACE_DIR)
	@cd $(@D) && \
        git clone -b libyang1 $($(@F)_GITHUB_URL) && \
        cd $(@F) && echo "-------------\n$(@F) revision: $$(git rev-parse HEAD)\n-------------"
