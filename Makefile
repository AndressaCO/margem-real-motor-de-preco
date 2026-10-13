.PHONY: install lint type test evals demo check

install:
	pip install -e ".[dev]"

lint:
	ruff check . && ruff format --check .

type:
	mypy

test:
	pytest -q --cov=margem_real --cov-fail-under=95

evals:
	python -m margem_real.agent.evals --trials 5 --saida evals
	python scripts/atualizar_readme.py

demo:
	python -m margem_real
	python -m margem_real.pipeline --skus 100

check: lint type test
	python scripts/auditar.py --rapido
