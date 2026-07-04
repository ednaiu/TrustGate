"""Generate LLM solutions for every task in tasks/.

Providers are picked by available env vars:
  OPENAI_API_KEY   -> gpt-4o-mini
  GIGACHAT_TOKEN   -> GigaChat (access token, see their docs for OAuth)

Raw responses are written to raw/<model>/<task_id>.json and never overwritten,
so the corpus stays reproducible (FR-EXP-2).
"""
import json
import os
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


PROVIDERS = {
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
    active = {name: fn for name, (env, fn) in PROVIDERS.items() if os.environ.get(env)}
    if not active:
        sys.exit("no API keys in env, nothing to do (see module docstring)")

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
