# {{cookiecutter.project_name}}

## What is this repository about?
{{cookiecutter.project_description}}

## How to setup a development environment?

### Docker and Docker Compose
This project uses `docker` and `docker-compose` to operate. Please install:

* [docker](https://docs.docker.com/get-docker/) ~= 20.10.17

before going any further.

## Makefile
`Makefile` is used in this project to automate calling some tasks. If you are on Windows, you can install `make` using
[chocolatey](https://chocolatey.org/) ( using: `choco install make` ). The default target ( `make` command without anything else)
is set to display short information about all available targets you can use:

```
Available rules:

build                          Build docker image 
check-type-annotations         Check type annotations using mypy 
clean                          Delete all compiled Python files 
down                           Stop docker containers 
exec-in                        Open an interactive shell in the app's docker container 
format                         Format code using black 
format-and-sort                Format and sort code using black and isort 
format-check                   Check format using blac 
full-check                     Perform a full check 
git-precommit-hook             Add precommit hook for git (use -n flag to skip validation) 
lint                           Lint coode using flake8 
lock-dependencies              Lock dependencies using pipenv 
push                           Push docker image to GCP Container Registry. Requires IMAGE_TAG to be specified. 
sort                           Sort code using isort 
sort-check                     Check sorting using isort 
test                           Run tests using pytest
train                          Train model (on remote VM) 
up                             Start docker containers 
up-ci                          Start docker containers for CI
...
```

## Dependency Management
[Poetry](https://python-poetry.org/) is used in this project as a dependency resolver. 
One can define both development and production dependencies in a single `pyproject.toml`, and choose
to install either both of them together, or only production dependencies. 

Initially, it takes longer to install all of the required packages (compared to pip), 
the reason is because Poetry needs to recursively check every dependency of every 
dependency and find versions of packages that works with every specified package. 
After the initial dependency resolution Poetry locks the versions of each package in a
`poetry.lock` file with additional information for deterministic builds. After this file
is created, Poetry doesn't need to resolve any dependencies, so installing packages becomes
almost as fast as `pip install ...`. `poetry.lock` can (and should) be tracked by `git`.

One thing to note that, whenever you change a dependency in `pyproject.toml` file, you have to
build the docker image again with updated dependencies. In order to do that you can run 
`make build-for-dependencies`. This is not something that you should strictly
remember about. Poetry will complain about it if the `pyproject.toml` doesn't match the `poetry.lock` file.

Lastly, while docker image is being build, Poetry resolves dependencies, and saves the 
`poetry.lock` in the docker container. Since we need this file also in our project's
repository, we need to copy it from docker container to our project. 
`make build-for-dependencies` will handle everything for you, so you don't need to worry about doint it
manually. Note that you don't always need this, because in usual circumstances
`poetry.lock` is already present in the repository. If you just need to build the docker image, and you
didn't modify any python dependencies in `pyproject.toml` file, you can simply run `make build`

## Building Docker Image

The docker image used in this repository is prepared with a [Dockerfile](./docker/Dockerfile),
you can take a look at it if you want to know more about it. In order to build the docker image
you can run:

```bash
make build
```

For project development (training, evaluation, ...) the `DEV=1` environmnet should be used. 
With this flag you can add things that you think they will be useful in the Docker image, but 
they won't be necessary for CI, or on production (if this Docker image will be used one day
on some production environmnet(?)).

#### Pushing the Docker image onto GCP Container Registry

If you would like to manually push the Docker image onto GCP Container Registry, you can use the command:

```bash
make push IMAGE_TAG=<image-tag>
```

## Building GCP Machine Image using Packer
[Packer](https://www.packer.io/plugins/builders/googlecompute) is used to automate the process of creating
[Machine Image](https://cloud.google.com/compute/docs/machine-images) that is used in {{cookiecutter.project_name}} training.
In order to install Packer, you can run:

```bash
make install-packer-for-debian
```

*Note:* This rule is only for Debian. If you need to install Packer for Mac, take a look at [here](https://learn.hashicorp.com/tutorials/packer/get-started-install-cli)

You can check [this](./{{cookiecutter.project_name}}_machine_image.pkr.hcl) file out to see the configuration of
current Machine Image that is being used for training/validation. If you perform any changes to this file,
in order to re-build the machine image you can run:

```bash
make packer-build
```

The machine image that is used is a simple Debian 10 image with Nvidia drivers. Packer is used to "initialize" this
machine image by installing Nvidia drivers + pulling Docker image from GCP Container Registery, so that the training will start faster. 

If you modified the Docker image significantly, you might consider pushing it the the GCP Container registery as a
new version (e.g. v2, v3, ...), and build a new Machine Image (with Packer).
In order to do that, don't forget to update the startup script located at: [./scripts/vm_startup/{{cookiecutter.project_name}}_gcp_image_creation_startup_script.sh](./scripts/vm_startup/{{cookiecutter.project_name}}_gcp_image_creation_startup_script.sh)

## Sorting/Formatting/Linting/Type Checking/Testing
You can use targets specified in the `Makefile` to sort/format/lint/type check/test your 
code.

* For formatting using [black](https://github.com/psf/black), run:

```bash
make format
```

* For sorting imports using [isort](https://github.com/PyCQA/isort), run:

```bash
make sort
```

* For formatting + sorting, run:

```bash
make format-and-sort
```

* For linting using [flake8](https://flake8.pycqa.org/en/latest/), run:

```bash
make lint
```

* For checking type annotations, using [mypy](https://github.com/python/mypy), run:

```bash
make check-type-annotations
```

* For running tests using [pytest](https://github.com/pytest-dev/pytest), run:

```bash
make test
```

* For running everything above at once, run:

```bash
make full-check
```

You can also add a pre-commit hook to git, so that everytime you commit something all of
the commands described above will be ran automatically for you. If any of the checks fail
your commit won't be accepted. You can add this pre-commit hook by running:

```bash
make git-precommit-hook
```

*Note:* If you installed the pre-commit hook, but want to skip validation for some specific
commit, you can use `-n` flag: `git commit -nm "Some commit message"`

## Other README.md files
In order to keep the documentation brief on each page it is splitted into related sub pages. You can find documentation about
other components in the following sub directories:

* [Deployment](./{{cookiecutter.project_name}}/deployment/)
* [Configuration](./{{cookiecutter.project_name}}/configs/)
* [Training](./{{cookiecutter.project_name}}/training/)
* [Launching the training](/{{cookiecutter.project_name}}/runner/)
* [Utils](./{{cookiecutter.project_name}}/utils/)
