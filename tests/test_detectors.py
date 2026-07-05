import pytest

from trustgate.detectors import ScanContext, run_static
from trustgate.known_packages import closest_popular, is_known

# (detector, snippet, should_fire) -- two positive and two negative cases each
CASES = [
    # TG-D01 hallucinated imports
    ("TG-D01", "import requsets\n", True),
    ("TG-D01", "import zxqqjkwm\n", True),
    ("TG-D01", "import json\n", False),
    ("TG-D01", "import collections\n", False),
    # TG-D02 non-existent attributes
    ("TG-D02", "import os\nos.path.exists_all('/tmp')\n", True),
    ("TG-D02", "from os.path import exists_all\n", True),
    ("TG-D02", "import os\nos.path.exists('/tmp')\n", False),
    ("TG-D02", "from os.path import exists\n", False),
    ("TG-D02", "import os.path\nprint(os.getcwd())\n", False),
    ("TG-D02", "from .json import helper\n", False),
    # TG-D03 dangerous execution
    ("TG-D03", "eval(user_input)\n", True),
    ("TG-D03", "import pickle\npickle.loads(data)\n", True),
    ("TG-D03", "x = compile('1', '<s>', 'eval')\n", False),
    ("TG-D03", "evaluate(x)\n", False),
    # TG-D04 sql injection
    ("TG-D04", "cur.execute(f'SELECT * FROM t WHERE id={uid}')\n", True),
    ("TG-D04", "cur.execute('SELECT * FROM t WHERE id=' + uid)\n", True),
    ("TG-D04", "cur.execute('SELECT * FROM t WHERE id=?', (uid,))\n", False),
    ("TG-D04", "cur.execute('SELECT * ' + 'FROM t ' + 'WHERE id=?')\n", False),
    # TG-D05 shell=True
    ("TG-D05", "import subprocess\nsubprocess.run(cmd, shell=True)\n", True),
    ("TG-D05", "import subprocess\nsubprocess.call(user_cmd, shell=True)\n", True),
    ("TG-D05", "import subprocess\nsubprocess.run(['ls', '-l'])\n", False),
    ("TG-D05", "import subprocess\nsubprocess.run(cmd, shell=False)\n", False),
    # TG-D06 verify=False
    ("TG-D06", "import requests\nrequests.get(url, verify=False)\n", True),
    ("TG-D06", "import requests\nrequests.post(url, data=d, verify=False)\n", True),
    ("TG-D06", "import requests\nrequests.get(url)\n", False),
    ("TG-D06", "import requests\nrequests.get(url, verify=True)\n", False),
    # TG-D07 weak hash for secrets
    ("TG-D07", "import hashlib\npassword_hash = hashlib.md5(pw.encode()).hexdigest()\n", True),
    ("TG-D07", "import hashlib\ntoken = hashlib.sha1(s.encode()).hexdigest()\n", True),
    ("TG-D07", "import hashlib\nchecksum = hashlib.md5(data).hexdigest()\n", False),
    ("TG-D07", "import hashlib\nfile_id = hashlib.sha1(blob).hexdigest()\n", False),
    # TG-D08 broad except
    ("TG-D08", "try:\n    f()\nexcept:\n    pass\n", True),
    ("TG-D08", "try:\n    f()\nexcept Exception:\n    pass\n", True),
    ("TG-D08", "try:\n    f()\nexcept ValueError:\n    pass\n", False),
    ("TG-D08", "try:\n    f()\nexcept:\n    raise\n", False),
    # TG-D09 stubs
    ("TG-D09", "def solve(a, b):\n    pass\n", True),
    ("TG-D09", "def solve(a, b):\n    raise NotImplementedError\n", True),
    ("TG-D09", "def solve(a, b):\n    return a + b\n", False),
    ("TG-D09", "from abc import abstractmethod\nclass A:\n    @abstractmethod\n    def f(self):\n        pass\n", False),
    # TG-D10 dead code
    ("TG-D10", "def f():\n    return 1\n    print('hi')\n", True),
    ("TG-D10", "if True:\n    x = 1\nelse:\n    x = 2\n", True),
    ("TG-D10", "def f():\n    return 1\n", False),
    ("TG-D10", "def f(x):\n    if x:\n        return 1\n    return 2\n", False),
    # TG-D13 hallucinated keyword arguments
    ("TG-D13", "import shutil\nshutil.copy(a, b, overwrite=True)\n", True),
    ("TG-D13", "from textwrap import dedent\ndedent(s, strip=True)\n", True),
    ("TG-D13", "import shutil\nshutil.copy(a, b, follow_symlinks=False)\n", False),
    ("TG-D13", "import json\njson.dumps(obj, indent=2)\n", False),
    ("TG-D13", "import subprocess\nsubprocess.run(cmd, check=True, capture_output=True)\n", False),
    # TG-D14 placeholder artifacts
    ("TG-D14", 'API_KEY = "your-api-key"\n', True),  # trustgate: ignore TG-D14
    ("TG-D14", 'token = "YOUR_API_KEY_HERE"\n', True),  # trustgate: ignore TG-D14
    ("TG-D14", 'conf = "<your password here>"\n', True),  # trustgate: ignore TG-D14
    ("TG-D14", 'url = "https://api.example.com/v1"\n', False),
    ("TG-D14", 'msg = "your order has shipped"\n', False),
    # TG-D11 tautological asserts
    ("TG-D11", "assert True\n", True),
    ("TG-D11", "assert f(x) == f(x)\n", True),
    ("TG-D11", "assert f(x) == 42\n", False),
    ("TG-D11", "assert a == b\n", False),
]


@pytest.mark.parametrize("detector,snippet,fires", CASES,
                         ids=[f"{d}-{'pos' if f else 'neg'}-{i}" for i, (d, _, f) in enumerate(CASES)])
def test_detector(detector, snippet, fires):
    hits = [f for f in run_static(snippet) if f.detector == detector]
    if fires:
        assert hits, f"{detector} should fire on:\n{snippet}"
    else:
        assert not hits, f"{detector} false positive on:\n{snippet}: {hits}"


def test_typo_import_is_critical_unknown_is_major():
    findings = {f.message: f for f in run_static("import requsets\nimport zxqqjkwm\n")}
    severities = {f.severity for f in findings.values()}
    assert severities == {"critical", "major"}


def test_findings_sorted_by_line():
    src = "def f():\n    pass\n\neval(x)\n"
    lines = [f.line for f in run_static(src)]
    assert lines == sorted(lines)


def test_inline_ignore_suppresses_one_detector():
    src = "assert f(x) == f(x)  # trustgate: ignore TG-D11\n"
    assert not run_static(src)


def test_todo_inside_string_is_not_comment():
    src = 'template = "# TODO generated sample\\n"\n'
    assert not [f for f in run_static(src) if f.detector == "TG-D09"]


# --- TG-D01 determinism (the verdict must not depend on the local env) ---

def test_d01_verdict_does_not_depend_on_local_env():
    # tomli is installed in some envs and not in others; the snapshot decides
    for module in ("tomli", "pytest", "zxqqjkwm"):
        default = is_known(module)
        assert default == is_known(module, trust_local_env=False)


def test_d01_snapshot_covers_popular_packages():
    for module in ("requests", "bs4", "PIL", "sklearn", "boto3"):
        assert is_known(module), module


def test_d01_first_party_modules_suppress_finding():
    src = "import trustgate_demo_app\n"
    assert [f for f in run_static(src) if f.detector == "TG-D01"]
    ctx = ScanContext(known_modules=frozenset({"trustgate_demo_app"}))
    assert not [f for f in run_static(src, ctx=ctx) if f.detector == "TG-D01"]


def test_typosquat_needs_five_chars():
    # short names are within distance 2 of half of PyPI: never call typosquat
    assert closest_popular("jso") is None
    assert closest_popular("requsets") is not None
