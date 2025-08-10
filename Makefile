# CONFIG
COMPOSE=docker compose
API=api

.PHONY: up down logs sh build migrate makemigration downgrade history stamp

up:
	$(COMPOSE) up -d --build

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f $(API)

sh:
	$(COMPOSE) exec $(API) sh

build:
	$(COMPOSE) build --no-cache

# --- Alembic (run inside the api container) ---
migrate:
	$(COMPOSE) run --rm -e PYTHONPATH=/app $(API) alembic -c /app/alembic.ini upgrade head

makemigration:
	@read -p "Message: " msg; \
	$(COMPOSE) run --rm -e PYTHONPATH=/app $(API) alembic -c /app/alembic.ini revision -m "$$msg" --autogenerate

history:
	$(COMPOSE) run --rm -e PYTHONPATH=/app $(API) alembic -c /app/alembic.ini history

downgrade:
	@read -p "Downgrade to (e.g. -1 or <rev>): " rev; \
	$(COMPOSE) run --rm -e PYTHONPATH=/app $(API) alembic -c /app/alembic.ini downgrade $$rev

stamp:
	@read -p "Stamp to (e.g. head or <rev>): " rev; \
	$(COMPOSE) run --rm -e PYTHONPATH=/app $(API) alembic -c /app/alembic.ini stamp $$rev


OPENAPI=openapi.json
WORKDIR=/work

openapi:
	curl -sS http://localhost:8000/openapi.json > $(OPENAPI)

docs-html: openapi
	docker run --rm -v $$PWD:$(WORKDIR) -w $(WORKDIR) \
		openapitools/openapi-generator-cli generate \
		-i $(OPENAPI) -g html2 -o docs/html

docs-redoc: openapi
	docker run --rm -v $$PWD:$(WORKDIR) -w $(WORKDIR) node:20-alpine \
		sh -lc "npm -g i redoc-cli && redoc-cli bundle $(OPENAPI) -o docs/index.html"

sdk-python: openapi
	docker run --rm -v $$PWD:$(WORKDIR) -w $(WORKDIR) \
		openapitools/openapi-generator-cli generate \
		-i $(OPENAPI) -g python -o sdks/python
