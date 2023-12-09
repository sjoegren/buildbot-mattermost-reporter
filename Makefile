PYTHON_PACKAGE = buildbot-mattermost-reporter
SRC = src
ENV = env

.PHONY: test build flake8 black checkformat unittest

test: flake8 checkformat unittest

build:
	python -m build

flake8: | $(ENV)
	$(ENV)/bin/flake8 $(SRC)

checkformat: | $(ENV)
	$(ENV)/bin/black --check --diff .

black: | $(ENV)
	$(ENV)/bin/black .

unittest: | $(ENV)
	$(ENV)/bin/pytest tests/

$(ENV):
	python3 -m venv $@
	$@/bin/pip install -e .
	$@/bin/pip install $(PYTHON_PACKAGE)[test]

clean:
	rm -rf $(ENV) dist
