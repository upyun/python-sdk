REQUIREMENTS="requirements.txt"
TAG="\n\n\033[0;32m\#\#\# "
END=" \#\#\# \033[0m\n"

all: init

uninstall-upyun:
	@echo $(TAG)Removing existing installation of upyun$(END)
	- pip uninstall --yes upyun >/dev/null
	@echo

uninstall-all: uninstall-upyun
	- pip uninstall --yes -r $(REQUIREMENTS)

init: uninstall-upyun
	@echo $(TAG)Installing requirements$(END)
	pip install --upgrade -r $(REQUIREMENTS)
	@echo $(TAG)Installing upyun$(END)
	pip install --upgrade --editable .
	@echo

test:
	@echo $(TAG)Running tests$(END)
	pip install pytest pytest-cov flake8
	flake8 upyun
	py.test --cov ./upyun --cov ./tests --verbose ./tests
	@echo

clean:
	@echo $(TAG)Cleaning up$(END)
	rm -rf .tox *.egg dist build .coverage
	find . -name '__pycache__' -delete -print -o -name '*.pyc' -delete -print
	@echo
