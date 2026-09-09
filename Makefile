.PHONY: install check test fmt

install:
	npm install

check:
	npm run lint

test:
	npm run test

fmt:
	@echo "No formatter configured"