"""Generate LLM solutions for every task in tasks/.

Providers are picked by what is available in the environment:
  OPENAI_API_KEY   -> gpt-4o-mini
  GIGACHAT_TOKEN   -> GigaChat (access token, see their docs for OAuth)
  claude CLI       -> claude-haiku / claude-sonnet (no key needed)

Raw responses are written to raw/<model>/<task_id>.json and never overwritten,
so the corpus stays reproducible (FR-EXP-2).
"""
import json
import os
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).parent
TASKS = HERE / "tasks"
RAW = HERE / "raw"

TEMPERATURE = 0.7
PROMPT = ("Solve this task in Python. Reply with a single ```python code block, "
          "no explanations.\n\n{task}")


def call_openai(task_text):
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps({
            "model": "gpt-4o-mini",
            "temperature": TEMPERATURE,
            "messages": [{"role": "user", "content": PROMPT.format(task=task_text)}],
        }).encode(),
        headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}",
                 "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.load(resp)
    return data["choices"][0]["message"]["content"], data


def call_gigachat(task_text):
    req = urllib.request.Request(
        "https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
        data=json.dumps({
            "model": "GigaChat",
            "temperature": TEMPERATURE,
            "messages": [{"role": "user", "content": PROMPT.format(task=task_text)}],
        }).encode(),
        headers={"Authorization": f"Bearer {os.environ['GIGACHAT_TOKEN']}",
                 "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.load(resp)
    return data["choices"][0]["message"]["content"], data


def call_claude_cli(model):
    def call(task_text):
        proc = subprocess.run(
            ["claude", "-p", "--model", model, PROMPT.format(task=task_text)],
            capture_output=True, text=True, timeout=300)
        if proc.returncode != 0:
            raise RuntimeError(f"claude CLI failed: {proc.stderr[-500:]}")
        reply = proc.stdout
        return reply, {"provider": "claude-cli", "model": model, "stdout": reply}
    return call


def _available_providers():
    active = {}
    for name, (env, fn) in API_PROVIDERS.items():
        if os.environ.get(env):
            active[name] = fn
    if shutil.which("claude"):
        active["claude-haiku"] = call_claude_cli("claude-haiku-4-5")
        active["claude-sonnet"] = call_claude_cli("claude-sonnet-5")
    return active


API_PROVIDERS = {
    "gpt-4o-mini": ("OPENAI_API_KEY", call_openai),
    "gigachat": ("GIGACHAT_TOKEN", call_gigachat),
}


def extract_code(reply: str) -> str:
    if "```" not in reply:
        return reply
    block = reply.split("```")[1]
    if block.startswith("python"):
        block = block[len("python"):]
    return block.strip() + "\n"


def main():
    active = _available_providers()
    if not active:
        sys.exit("no API keys in env and no claude CLI, nothing to do (see module docstring)")

    tasks = sorted(p for p in TASKS.iterdir() if (p / "prompt.md").is_file())
    print(f"{len(tasks)} tasks x {len(active)} models")

    for model, call in active.items():
        outdir = RAW / model
        outdir.mkdir(parents=True, exist_ok=True)
        for task in tasks:
            out = outdir / f"{task.name}.json"
            if out.exists():
                continue  # keep raw data immutable
            reply, full = call((task / "prompt.md").read_text(encoding="utf-8"))
            out.write_text(json.dumps({
                "model": model, "temperature": TEMPERATURE, "task": task.name,
                "code": extract_code(reply), "raw_response": full,
            }, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"  {model}/{task.name}")


if __name__ == "__main__":
    main()
