.PHONY: test

test:
	rm -rf .agentsea && \
	poetry run pytest -vvv -s