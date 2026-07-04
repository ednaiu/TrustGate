.PHONY: test coverage experiment demo

test:
	pytest -q

coverage:
	pytest --cov=trustgate --cov-fail-under=80 -q

demo:
	@printf 'import requsets\ndef get(url):\n    return eval(url)\n' > /tmp/tg_demo.py
	-trustgate check /tmp/tg_demo.py --no-sandbox
	@rm -f /tmp/tg_demo.py

experiment:
	python experiment/generate_corpus.py
	python experiment/run_experiment.py --label
	python experiment/inject_defects.py
	python experiment/run_experiment.py --measure
