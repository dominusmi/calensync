start-database:
	docker compose -f docker/database-compose.yaml up -d

stop-database:
	docker compose -f docker/database-compose.yaml down

start-api:
	uvicorn api.src.api:app --reload --env-file .env