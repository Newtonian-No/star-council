"""
星海理事会 — 理事基类和 Spawner

每个理事 = 一个独立的 Hermes 子进程。
通过 config.yaml 配置模型、provider、toolsets。
"""

import os
import subprocess
import yaml
import tempfile
from pathlib import Path
from typing import Optional


class StarCouncilConfig:
    """加载 config.yaml"""

    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config.yaml"
        with open(config_path) as f:
            self.data = yaml.safe_load(f)

    def get_councilor(self, name: str) -> dict:
        return self.data["councilors"].get(name, {})

    def get_weights(self, stage: str) -> dict:
        return self.data["weights"].get(stage, {})

    @property
    def max_rounds(self) -> int:
        return self.data.get("meeting", {}).get("max_rounds", 10)

    @property
    def project_root(self) -> Path:
        return Path(__file__).parent.parent


class CouncilorSpawner:
    """启动一个理事子进程"""

    def __init__(self, config: StarCouncilConfig):
        self.config = config

    def spawn(
        self,
        councilor_name: str,
        prompt: str,
        workdir: str = None,
    ) -> str:
        """
        启动一个理事子进程并返回输出。

        Args:
            councilor_name: architect/experiment/literature/writer/devil
            prompt: 发给理事的完整 prompt（包含上下文 + 任务）
            workdir: 工作目录

        Returns:
            理事的 stdout 输出
        """
        cfg = self.config.get_councilor(councilor_name)
        if not cfg:
            return f"[ERROR] 未知理事: {councilor_name}"

        provider = cfg["provider"]
        model = cfg["model"]
        toolsets = cfg.get("toolsets", ["file"])
        timeout = cfg.get("timeout", 300)

        # 把 prompt 写入临时文件（避免 shell 转义问题）
        prompt_file = tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, dir="/tmp", encoding="utf-8"
        )
        prompt_file.write(prompt)
        prompt_file.close()

        # 构建命令
        if provider == "openrouter":
            return self._spawn_openrouter(cfg, prompt_file.name, toolsets, timeout, workdir)
        else:
            return self._spawn_direct(provider, model, prompt_file.name, toolsets, timeout, workdir)

    def _spawn_direct(self, provider, model, prompt_file, toolsets, timeout, workdir):
        """DeepSeek 直连 sprawn"""
        toolsets_str = ",".join(toolsets)
        cmd = [
            "hermes", "chat",
            "--provider", provider,
            "--model", model,
            "--toolsets", toolsets_str,
            "-Q", "--yolo",
            "-q", f"$(cat {prompt_file})",
        ]

        result = subprocess.run(
            " ".join(cmd),
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=workdir or str(self.config.project_root),
        )
        os.unlink(prompt_file)
        return result.stdout if result.returncode == 0 else f"[ERROR] {result.stderr}"

    def _spawn_openrouter(self, cfg, prompt_file, toolsets, timeout, workdir):
        """OpenRouter spawn — 需要 VPN 代理 + API key 注入"""
        toolsets_str = ",".join(toolsets)
        proxy = cfg.get("proxy", "http://127.0.0.1:7890")

        # 用 bash -c 注入环境变量
        wrapper_cmd = (
            f"export HTTPS_PROXY={proxy} && "
            f"export HTTP_PROXY={proxy} && "
            f"hermes chat "
            f"--provider openrouter "
            f"--model {cfg['model']} "
            f"--toolsets {toolsets_str} "
            f"-Q --yolo "
            f'-q "$(cat {prompt_file})"'
        )

        result = subprocess.run(
            ["bash", "-c", wrapper_cmd],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=workdir or str(self.config.project_root),
        )
        os.unlink(prompt_file)
        return result.stdout if result.returncode == 0 else f"[ERROR] {result.stderr}"


# === 便捷函数 ===

def load_prompt(councilor_name: str) -> str:
    """加载理事的 system prompt 模板"""
    prompt_path = Path(__file__).parent.parent / "prompts" / f"{councilor_name}.md"
    if prompt_path.exists():
        return prompt_path.read_text(encoding="utf-8")
    return f"你是星海理事会的{councilor_name}。请基于上下文发言。"


def speak(councilor_name: str, context: str, task: str = "") -> str:
    """让一个理事发言"""
    config = StarCouncilConfig()
    spawner = CouncilorSpawner(config)

    system = load_prompt(councilor_name)
    full_prompt = f"{system}\n\n---\n\n## 当前讨论上下文\n\n{context}\n\n---\n\n"
    if task:
        full_prompt += f"## 你的任务\n\n{task}\n\n"
    full_prompt += f"请以{councilor_name}的身份发言。用中文讨论，技术术语保留英文。"

    return spawner.spawn(councilor_name, full_prompt)


# === CLI 测试入口 ===

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python councilor.py <councilor_name> [task]")
        print("  councilor_name: architect/experiment/literature/writer/devil")
        sys.exit(1)

    name = sys.argv[1]
    task = sys.argv[2] if len(sys.argv) > 2 else ""

    context = """这是星海理事会第一次测试会议。
议题：评估一个关于 GFR 肾小球滤过率自动估算的论文 idea。
核心方法：UNet3+ 结合 Mamba State-Space Model 和 Deformable Convolution。
当前阶段：ideation（idea 探索）。"""

    print(f"\n{'='*60}")
    print(f"  召集中：{name}")
    print(f"{'='*60}\n")
    result = speak(name, context, task)
    print(result)
