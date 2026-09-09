.PHONY: install check test fmt

install:
	npm install

check:
	npm run lint

test:
	npm run test

fmt:
	npm run format