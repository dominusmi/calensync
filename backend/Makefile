start-database:
	docker compose -f docker/database-compose.yaml up -d

stop-database:
	docker compose -f docker/database-compose.yaml down

start-api:
	python3 api/local/build.py
	FLASK_ENV=development FLASK_APP=api/local/local_api ENV=local python api/local/local_api.py