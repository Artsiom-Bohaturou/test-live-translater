#!/usr/bin/env python3
"""Pull an Ollama model through the already-running Compose ollama service."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def load_dotenv(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def compose_base_command(use_gpu: bool) -> list[str]:
    command = ["docker", "compose", "-f", "compose.yaml"]
    if use_gpu:
        command.extend(["-f", "compose.gpu.yaml"])
    return command


def run(command: list[str], env: dict[str, str]) -> int:
    print("$ " + " ".join(command), flush=True)
    process = subprocess.Popen(command, cwd=REPO_ROOT, env=env)
    return process.wait()


def wait_for_ollama(base_command: list[str], env: dict[str, str], attempts: int) -> bool:
    for attempt in range(1, attempts + 1):
        code = run(base_command + ["exec", "-T", "ollama", "ollama", "list"], env)
        if code == 0:
            return True
        sleep_seconds = min(attempt * 3, 15)
        print(f"Ollama is not ready yet; retrying in {sleep_seconds}s...", flush=True)
        time.sleep(sleep_seconds)
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", help="Ollama model to pull. Defaults to OLLAMA_MODEL from .env or qwen2.5:7b.")
    parser.add_argument("--gpu", action="store_true", help="Include compose.gpu.yaml when executing docker compose commands.")
    parser.add_argument("--retries", type=int, default=5, help="Number of pull attempts after Ollama is ready.")
    args = parser.parse_args()

    dotenv = load_dotenv(REPO_ROOT / ".env")
    env = os.environ.copy()
    env.update(dotenv)
    model = args.model or env.get("OLLAMA_MODEL") or "qwen2.5:7b"
    base_command = compose_base_command(args.gpu)

    if not wait_for_ollama(base_command, env, attempts=10):
        print("Ollama service did not become ready. Run `docker compose up -d ollama` first.", file=sys.stderr)
        return 1

    for attempt in range(1, args.retries + 1):
        code = run(base_command + ["exec", "-T", "ollama", "ollama", "pull", model], env)
        if code == 0:
            print(f"Pulled {model} through the running Compose ollama service.")
            return 0
        sleep_seconds = min(attempt * 10, 60)
        print(f"Pull failed on attempt {attempt}/{args.retries}; retrying in {sleep_seconds}s...", flush=True)
        time.sleep(sleep_seconds)

    print(f"Failed to pull {model} after {args.retries} attempts.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
