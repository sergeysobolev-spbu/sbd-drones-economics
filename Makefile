dummy:
	@echo tbd

setup: dummy

run-all: build-all dummy

run-all-docker: build-all-docker dummy

build-all: dummy

build-all-docker: dummy

tests-all: build-all dummy

tests-all-docker: build-all-docker dummy

clean: dummy

clean-all-docker: dummy