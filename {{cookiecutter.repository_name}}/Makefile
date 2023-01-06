# Make all targets .PHONY
.PHONY: $(shell sed -n -e '/^$$/ { n ; /^[^ .\#][^ ]*:/ { s/:.*$$// ; p ; } ; }' $(MAKEFILE_LIST))

include .envs/.app
export

DEBUG = true
SHELL = /usr/bin/env bash
USER_NAME = $(shell whoami)
HOST_NAME = $(shell hostname)

PROD_SERVICE_NAME=app-prod
PROD_CONTAINER_NAME={{cookiecutter.project_name}}-prod

ifeq (, $(shell which nvidia-smi))
	PROFILE = ci
	CONTAINER_NAME = {{cookiecutter.project_name}}-ci
	SERVICE_NAME = app-ci
	DOCKER_RUN = docker run --init --rm --network host --ipc host --user root --privileged --log-driver=gcplogs
else
	PROFILE = dev
	CONTAINER_NAME = {{cookiecutter.project_name}}-dev
	SERVICE_NAME = app-dev
	DOCKER_RUN = docker run --init --rm --gpus all --network host --ipc host --user root --privileged --log-driver=gcplogs
endif

ifeq (, $(shell which docker-compose))
	DOCKER_COMPOSE_COMMAND = docker compose
else
	DOCKER_COMPOSE_COMMAND = docker-compose
endif

DIRS_TO_VALIDATE={{cookiecutter.project_name}} tests

DOCKER_COMPOSE_RUN = $(DOCKER_COMPOSE_COMMAND) run --rm $(SERVICE_NAME)
DOCKER_COMPOSE_RUN_PROD = $(DOCKER_COMPOSE_COMMAND) run --rm $(PROD_SERVICE_NAME)

DOCKER_COMPOSE_EXEC = $(DOCKER_COMPOSE_COMMAND) exec $(SERVICE_NAME)
DOCKER_COMPOSE_EXEC_PROD = $(DOCKER_COMPOSE_COMMAND) exec -T $(PROD_SERVICE_NAME)

LOCAL_DOCKER_IMAGE_NAME = {{cookiecutter.project_name}}
DOCKER_IMAGE_CACHE = $(LOCAL_DOCKER_IMAGE_NAME):latest
# HOST-NAME/PROJECT-ID/REPOSITORY/IMAGE
GCP_DOCKER_IMAGE_NAME = {{cookiecutter.gcp_docker_image_name}}
DOCKER_IMAGE_TAG := $(shell echo "$$(uuidgen)")

GCP_DISK_IMAGE_CONFIG = ./{{cookiecutter.project_name}}_machine_image.pkr.hcl

lock-dependencies: BUILD_POETRY_LOCK = /home/$(USER_NAME)/poetry.lock.build 

define PRE_COMMIT_SCRIPT
#!/usr/bin/env bash

set -xeEuo pipefail

make _git-run-precommit-hook
endef

export PRE_COMMIT_SCRIPT

# Returns true if the stem is a non-empty environment variable, or else raises an error.
guard-%:
	@#$(or ${$*}, $(error $* is not set))


## Generate final config. For overrides use: OVERRIDES=<overrides>
generate-final-config: up-prod
	@$(DOCKER_COMPOSE_EXEC_PROD) python ./{{cookiecutter.project_name}}/generate_final_config.py --overrides ${OVERRIDES}

## Generate final config. For overrides use: OVERRIDES=<overrides>
generate-final-config-local: up
	@$(DOCKER_COMPOSE_EXEC) python ./{{cookiecutter.project_name}}/generate_final_config.py --overrides ${OVERRIDES}

## Train model
local-train: generate-final-config-local push-automatic
	@$(DOCKER_COMPOSE_EXEC) python ./{{cookiecutter.project_name}}/train.py

## Train model
train: generate-final-config push
	@$(DOCKER_COMPOSE_EXEC_PROD) python ./{{cookiecutter.project_name}}/train_remote.py

## Evaluate model
local-evaluate: up
	@$(DOCKER_COMPOSE_EXEC) python ./{{cookiecutter.project_name}}/evaluate.py

## push docker image DockerHub
push-automatic: build-for-registery guard-DOCKER_IMAGE_TAG
ifneq ($(DEBUG),true)
	gcloud auth configure-docker --quiet {{cookiecutter.gcp_docker_registry}}-docker.pkg.dev
	docker tag $(LOCAL_DOCKER_IMAGE_NAME):latest $(GCP_DOCKER_IMAGE_NAME):"$${DOCKER_IMAGE_TAG}"
	docker push $(GCP_DOCKER_IMAGE_NAME):"$${DOCKER_IMAGE_TAG}"
endif

## push docker image DockerHub
push: build guard-DOCKER_IMAGE_TAG
	gcloud auth configure-docker --quiet {{cookiecutter.gcp_docker_registry}}-docker.pkg.dev
	docker tag $(LOCAL_DOCKER_IMAGE_NAME):latest $(GCP_DOCKER_IMAGE_NAME):"$${DOCKER_IMAGE_TAG}"
	docker push $(GCP_DOCKER_IMAGE_NAME):"$${DOCKER_IMAGE_TAG}"

## starts jupyter lab
notebook: up
	$(DOCKER_COMPOSE_EXEC) jupyter-lab --ip 0.0.0.0 --port 8888 --no-browser

## Sort code using isort
sort: up
	$(DOCKER_COMPOSE_EXEC) isort --atomic $(DIRS_TO_VALIDATE)

## Check sorting using isort
sort-check: up
	$(DOCKER_COMPOSE_EXEC) isort --check-only --atomic $(DIRS_TO_VALIDATE)

## Format code using black
format: up
	$(DOCKER_COMPOSE_EXEC) black $(DIRS_TO_VALIDATE)

## Check format using black
format-check: up
	$(DOCKER_COMPOSE_EXEC) black --check $(DIRS_TO_VALIDATE)

## Format and sort code using black and isort
format-and-sort: sort format

## Lint code using flake8
lint: up format-check sort-check
	$(DOCKER_COMPOSE_EXEC) flake8 $(DIRS_TO_VALIDATE)

## Check type annotations with mypy
check-type-annotations: up
	$(DOCKER_COMPOSE_EXEC) mypy $(DIRS_TO_VALIDATE)

## Run tests with pytest
test: up
	$(DOCKER_COMPOSE_EXEC) pytest

## Perform a full check
full-check: lint
	$(DOCKER_COMPOSE_EXEC) pytest --cov --cov-report xml --verbose

## Builds docker container.
build:
	$(DOCKER_COMPOSE_COMMAND) build $(SERVICE_NAME)

## Build for pushing to docker registery
build-for-registery:
ifneq ($(DEBUG),true)
	$(DOCKER_COMPOSE_COMMAND) build $(SERVICE_NAME)
endif

## Remove poetry.lock and builds docker container.
build-for-dependencies:
	rm -f *.lock
	$(DOCKER_COMPOSE_COMMAND) build $(SERVICE_NAME)

## docker-compose up -d
up:
ifeq (, $(shell docker ps -a | grep $(CONTAINER_NAME)))
	@make down
endif
	@$(DOCKER_COMPOSE_COMMAND) --profile $(PROFILE) up -d --remove-orphans

## Start docker containers for prod
up-prod:
ifeq ($(shell docker ps | grep $(PROD_CONTAINER_NAME)),)
	make down
endif
	$(DOCKER_COMPOSE_COMMAND) --profile prod up -d --remove-orphans


## docker-compose down
down:
	$(DOCKER_COMPOSE_COMMAND) down

## docker exec -it {{cookiecutter.project_name}} bash
exec-in: up
	docker exec -it $(CONTAINER_NAME) bash

## Lock dependencies with poetry
lock-dependencies: build-for-dependencies
	$(DOCKER_COMPOSE_RUN) bash -c "if [ -e $(BUILD_POETRY_LOCK) ]; then cp $(BUILD_POETRY_LOCK) ./poetry.lock; else poetry lock; fi"

## Create venv with required packages
create-venv:
	poetry install --sync

## Delete all compiled Python files
clean:
	find . -type f -name "*.py[co]" -delete
	find . -type d -name "__pycache__" -delete

## Install packer for Debian
install-packer-for-debian:
	curl -fsSL https://apt.releases.hashicorp.com/gpg | sudo apt-key add -
	sudo apt-add-repository "deb [arch=amd64] https://apt.releases.hashicorp.com $(shell lsb_release -cs) main"
	sudo apt-get update && sudo apt-get install packer

## Initialize Packer
packer-init:
	packer init $(GCP_DISK_IMAGE_CONFIG)

## Format Packer file
packer-format:
	packer fmt $(GCP_DISK_IMAGE_CONFIG)

## Validate Packer file
packer-validate:
	packer validate --var username=$(USER) $(GCP_DISK_IMAGE_CONFIG)

## Build GCP image using Packer
packer-build: packer-init packer-format packer-validate
	packer build --var username=$(USER) --force $(GCP_DISK_IMAGE_CONFIG)

## Install git precommit hook
git-precommit-hook:
ifneq ($(wildcard .git/hooks/pre-commit),)
	@echo "Precommit hook is already installed..."
else
	REPO_DIR="$(shell git rev-parse --show-toplevel)"; \
	PRE_COMMIT_SCRIPT_PATH="$${REPO_DIR}/.git/hooks/pre-commit"; \
	echo "$${PRE_COMMIT_SCRIPT}" >> "$${PRE_COMMIT_SCRIPT_PATH}"; \
	chmod 0755 "$${PRE_COMMIT_SCRIPT_PATH}"
endif

_git-run-precommit-hook: format lint sort-check-only
	@echo "Done..."

_run-from-utils: guard-FN
	@source ./scripts/utils.sh && $${FN} $${ARGS}

.DEFAULT_GOAL := help

# Inspired by <http://marmelab.com/blog/2016/02/29/auto-documented-makefile.html>
# sed script explained:
# /^##/:
# 	* save line in hold space
# 	* purge line
# 	* Loop:
# 		* append newline + line to hold space
# 		* go to next line
# 		* if line starts with doc comment, strip comment character off and loop
# 	* remove target prerequisites
# 	* append hold space (+ newline) to line
# 	* replace newline plus comments by `---`
# 	* print line
# Separate expressions are necessary because labels cannot be delimited by
# semicolon; see <http://stackoverflow.com/a/11799865/1968>
.PHONY: help
help:
	@echo "$$(tput bold)Available rules:$$(tput sgr0)"
	@echo
	@sed -n -e "/^## / { \
		h; \
		s/.*//; \
		:doc" \
		-e "H; \
		n; \
		s/^## //; \
		t doc" \
		-e "s/:.*//; \
		G; \
		s/\\n## /---/; \
		s/\\n/ /g; \
		p; \
	}" ${MAKEFILE_LIST} \
	| LC_ALL='C' sort --ignore-case \
	| awk -F '---' \
		-v ncol=$$(tput cols) \
		-v indent=36 \
		-v col_on="$$(tput setaf 6)" \
		-v col_off="$$(tput sgr0)" \
	'{ \
		printf "%s%*s%s ", col_on, -indent, $$1, col_off; \
		n = split($$2, words, " "); \
		line_length = ncol - indent; \
		for (i = 1; i <= n; i++) { \
			line_length -= length(words[i]) + 1; \
			if (line_length <= 0) { \
				line_length = ncol - indent - length(words[i]) - 1; \
				printf "\n%*s ", -indent, " "; \
			} \
			printf "%s ", words[i]; \
		} \
		printf "\n"; \
	}' \
	| more $(shell test $(shell uname) = Darwin && echo '--no-init --raw-control-chars')
