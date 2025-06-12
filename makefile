run:
	uvicorn app:app --reload 

test:
	pytest -m tests/routes/unit --capture=no

test-e2e:
	python -m pytest tests/routes/integration --capture=no

lint:
	flake8 app/

migration:
	alembic upgrade head

revert-migration:
	alembic downgrade -1