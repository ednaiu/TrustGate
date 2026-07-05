import importlib.util
from pathlib import Path

MODULE_PATH = Path(__file__).parent.parent / "experiment" / "benchmark_external.py"
SPEC = importlib.util.spec_from_file_location("benchmark_external", MODULE_PATH)
bench = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bench)


def test_confusion_matrix():
    result = bench.confusion([True, True, False, False], [True, False, True, False])

    assert result["tp"] == 1
    assert result["fn"] == 1
    assert result["fp"] == 1
    assert result["tn"] == 1


def test_external_benchmark_marks_missing_large_corpus():
    corpus = [
        {"id": "clean", "label": "clean", "code": "def add(a, b):\n    return a + b\n"},
        {"id": "bad", "label": "defective", "code": "def run(x):\n    return eval(x)\n"},
    ]

    result = bench.evaluate(corpus, min_samples=100)

    assert result["status"] == "needs_corpus"
    assert result["samples"] == 2
    assert "trustgate" in result["metrics"]
    assert "ablation" in result
