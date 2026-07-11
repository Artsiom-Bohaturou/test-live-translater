"""Tkinter desktop manager for local Docker/Ollama setup."""

from __future__ import annotations

import os
import queue
import subprocess
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from urllib.error import URLError
from urllib.request import urlopen

REPO_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = REPO_ROOT / ".env"
DEFAULTS = {
    "WHISPER_MODEL": "small",
    "WHISPER_DEVICE": "cpu",
    "WHISPER_COMPUTE_TYPE": "int8",
    "OLLAMA_MODEL": "qwen2.5:7b",
    "OLLAMA_TEMPERATURE": "0.2",
    "OLLAMA_NUM_PREDICT": "256",
    "HF_TOKEN": "",
}


class DesktopApp(tk.Tk):
    """Small GUI for configuring and operating the local assistant stack."""

    def __init__(self) -> None:
        super().__init__()
        self.title("Live Tab Audio Assistant Manager")
        self.geometry("880x680")
        self.log_queue: queue.Queue[str] = queue.Queue()
        self.vars = {key: tk.StringVar(value=value) for key, value in DEFAULTS.items()}
        self.use_gpu = tk.BooleanVar(value=False)
        self._load_env()
        self._build_ui()
        self.after(100, self._drain_logs)

    def _build_ui(self) -> None:
        root = ttk.Frame(self, padding=16)
        root.pack(fill=tk.BOTH, expand=True)

        config = ttk.LabelFrame(root, text="Configuration", padding=12)
        config.pack(fill=tk.X)
        rows = [
            ("Ollama model", "OLLAMA_MODEL", "Example: qwen2.5:7b, mistral:7b, llama3.1:8b"),
            ("Whisper model", "WHISPER_MODEL", "Example: small for speed, medium for accuracy"),
            ("Whisper device", "WHISPER_DEVICE", "Use cpu or cuda"),
            ("Whisper compute type", "WHISPER_COMPUTE_TYPE", "Use int8 for CPU or float16 for CUDA"),
            ("Ollama temperature", "OLLAMA_TEMPERATURE", "Lower values are more deterministic"),
            ("Ollama max tokens", "OLLAMA_NUM_PREDICT", "Keep small for low latency"),
            ("Hugging Face token", "HF_TOKEN", "Optional, avoids unauthenticated HF Hub rate-limit warnings"),
        ]
        for index, (label, key, help_text) in enumerate(rows):
            ttk.Label(config, text=label).grid(row=index, column=0, sticky=tk.W, pady=4)
            show = "*" if key == "HF_TOKEN" else ""
            ttk.Entry(config, textvariable=self.vars[key], show=show, width=42).grid(row=index, column=1, sticky=tk.EW, padx=8, pady=4)
            ttk.Label(config, text=help_text, foreground="#555").grid(row=index, column=2, sticky=tk.W, pady=4)
        config.columnconfigure(1, weight=1)

        ttk.Checkbutton(
            config,
            text="Use NVIDIA GPU Compose override",
            variable=self.use_gpu,
            command=self._apply_gpu_defaults,
        ).grid(row=len(rows), column=1, sticky=tk.W, pady=8)

        buttons = ttk.Frame(root)
        buttons.pack(fill=tk.X, pady=12)
        actions = [
            ("Save settings", self.save_env),
            ("Start services", self.start_services),
            ("Stop services", self.stop_services),
            ("Pull selected Ollama model", self.pull_model),
            ("List Ollama models", self.list_models),
            ("Health check", self.health_check),
            ("Open Chrome extension folder", self.open_extension_folder),
        ]
        for text, command in actions:
            ttk.Button(buttons, text=text, command=command).pack(side=tk.LEFT, padx=4, pady=4)

        guide = ttk.LabelFrame(root, text="Quick guide", padding=12)
        guide.pack(fill=tk.X, pady=(0, 12))
        ttk.Label(
            guide,
            justify=tk.LEFT,
            text=(
                "1. Save settings. Add HF_TOKEN if you have one to avoid unauthenticated Hugging Face downloads.\n"
                "2. Start services, then pull the selected Ollama model.\n"
                "3. Confirm Health check returns ok.\n"
                "4. Open chrome://extensions, enable Developer mode, and Load unpacked from the extension folder.\n"
                "5. In the extension popup click Start capture, then Ask about last 25s."
            ),
        ).pack(anchor=tk.W)

        log_frame = ttk.LabelFrame(root, text="Output", padding=8)
        log_frame.pack(fill=tk.BOTH, expand=True)
        self.log = tk.Text(log_frame, wrap=tk.WORD, height=18)
        self.log.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(log_frame, command=self.log.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log.configure(yscrollcommand=scrollbar.set)

    def _load_env(self) -> None:
        if not ENV_FILE.exists():
            return
        for line in ENV_FILE.read_text().splitlines():
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            if key in self.vars:
                self.vars[key].set(value)
        self.use_gpu.set(self.vars["WHISPER_DEVICE"].get() == "cuda")

    def _compose_command(self, *args: str) -> list[str]:
        command = ["docker", "compose", "-f", "compose.yaml"]
        if self.use_gpu.get():
            command.extend(["-f", "compose.gpu.yaml"])
        command.extend(args)
        return command

    def _apply_gpu_defaults(self) -> None:
        if self.use_gpu.get():
            self.vars["WHISPER_DEVICE"].set("cuda")
            self.vars["WHISPER_COMPUTE_TYPE"].set("float16")
        else:
            self.vars["WHISPER_DEVICE"].set("cpu")
            self.vars["WHISPER_COMPUTE_TYPE"].set("int8")

    def _env(self) -> dict[str, str]:
        env = os.environ.copy()
        env.update({key: var.get() for key, var in self.vars.items()})
        return env

    def save_env(self) -> None:
        lines = ["# Generated by the Live Tab Audio Assistant desktop manager."]
        for key in DEFAULTS:
            lines.append(f"{key}={self.vars[key].get()}")
        ENV_FILE.write_text("\n".join(lines) + "\n")
        self._write_log(f"Saved settings to {ENV_FILE}\n")

    def start_services(self) -> None:
        self.save_env()
        self._run(self._compose_command("up", "--build", "-d"), "Starting services")

    def stop_services(self) -> None:
        self._run(self._compose_command("down"), "Stopping services")

    def pull_model(self) -> None:
        model = self.vars["OLLAMA_MODEL"].get().strip()
        if not model:
            messagebox.showerror("Missing model", "Set OLLAMA_MODEL before pulling.")
            return
        self.save_env()
        self._run(self._compose_command("exec", "ollama", "ollama", "pull", model), f"Pulling {model}")

    def list_models(self) -> None:
        self._run(self._compose_command("exec", "ollama", "ollama", "list"), "Listing Ollama models")

    def health_check(self) -> None:
        def check() -> None:
            self.log_queue.put("\n$ curl http://127.0.0.1:8765/api/health\n")
            try:
                with urlopen("http://127.0.0.1:8765/api/health", timeout=5) as response:
                    self.log_queue.put(response.read().decode() + "\n")
            except URLError as exc:
                self.log_queue.put(f"Health check failed: {exc}\n")

        threading.Thread(target=check, daemon=True).start()

    def open_extension_folder(self) -> None:
        extension_path = REPO_ROOT / "extension"
        self.clipboard_clear()
        self.clipboard_append(str(extension_path))
        self._write_log(f"Extension folder copied to clipboard: {extension_path}\n")
        messagebox.showinfo("Extension folder", f"Path copied to clipboard:\n{extension_path}")

    def _run(self, command: list[str], title: str) -> None:
        def target() -> None:
            self.log_queue.put(f"\n## {title}\n$ {' '.join(command)}\n")
            try:
                process = subprocess.Popen(
                    command,
                    cwd=REPO_ROOT,
                    env=self._env(),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                )
            except FileNotFoundError:
                self.log_queue.put("Docker was not found. Install Docker Desktop or Docker Engine with Compose.\n")
                return
            assert process.stdout is not None
            for line in process.stdout:
                self.log_queue.put(line)
            self.log_queue.put(f"Command exited with code {process.wait()}\n")

        threading.Thread(target=target, daemon=True).start()

    def _write_log(self, text: str) -> None:
        self.log.insert(tk.END, text)
        self.log.see(tk.END)

    def _drain_logs(self) -> None:
        while True:
            try:
                self._write_log(self.log_queue.get_nowait())
            except queue.Empty:
                break
        self.after(100, self._drain_logs)


def main() -> None:
    app = DesktopApp()
    app.mainloop()


if __name__ == "__main__":
    main()
