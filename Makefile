.PHONY: test coverage scan benchmark benchmark-external dashboard demo-report experiment demo

test:
	pytest -q

coverage:
	pytest --cov=trustgate --cov-fail-under=80 -q

scan:
	trustgate scan . --project-tests "python -m pytest -q" --project-mutation --project-mutation-limit 10 --json trustgate-scan.json --html trustgate-scan.html --sarif trustgate.sarif --github-annotations trustgate-annotations.json --save-history trustgate-history.sqlite

benchmark:
	python experiment/static_benchmark.py

benchmark-external:
	python experiment/benchmark_external.py --corpus experiment/static_benchmark_cases.json --out benchmark-external.json

dashboard:
	trustgate dashboard --db trustgate-history.sqlite --html trustgate-dashboard.html

demo-report:
	trustgate check examples/block_solution.py.example --no-sandbox --html trustgate-demo.html

demo:
	@printf 'import requsets\ndef get(url):\n    return eval(url)\n' > /tmp/tg_demo.py
	-trustgate check /tmp/tg_demo.py --no-sandbox
	@rm -f /tmp/tg_demo.py

experiment:
	python experiment/generate_corpus.py
	python experiment/run_experiment.py --label
	python experiment/inject_defects.py
	python experiment/run_experiment.py --measure
