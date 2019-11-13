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
	wget http://yejingx.b0.upaiyun.com/python_sdk/mid.mp4 -O /tmp/test.mp4
	pip install --upgrade pytest pytest-cov flake8 tornado
	flake8 upyun tests --ignore=E402,E226,W504
	python examples/auth_server.py > /dev/null 2>&1 &
	py.test --cov ./upyun --cov ./tests --verbose ./tests
	ps aux | grep 'auth_server.py' | grep -v grep | awk '{print $$2}' | xargs kill -9
	rm -f /tmp/test.mp4
	@echo

clean:
	@echo $(TAG)Cleaning up$(END)
	rm -rf .tox *.egg dist build .coverage
	find . -name '__pycache__' -delete -print -o -name '*.pyc' -delete -print
	@echo
