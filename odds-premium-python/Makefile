run:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

lint:
	python -m py_compile $$(find app -name '*.py' | sort)
