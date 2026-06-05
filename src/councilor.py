"""
星海理事会 — 理事基类和 Spawner

每个理事 = 一个独立的 Hermes 子进程。
通过 config.yaml 配置模型、provider、toolsets。
"""

import os
import subprocess
import yaml
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

        # 构建命令 — prompt 直接作为 -z 参数（subprocess list 模式，不需要 shell 转义）
        if provider == "openrouter":
            return self._spawn_openrouter(cfg, prompt, toolsets, timeout, workdir)
        else:
            return self._spawn_direct(provider, model, prompt, toolsets, timeout, workdir)

    def _spawn_direct(self, provider, model, prompt, toolsets, timeout, workdir):
        """DeepSeek 直连"""
        toolsets_str = ",".join(toolsets)
        cmd = [
            "hermes", "chat",
            "--provider", provider,
            "--model", model,
            "--toolsets", toolsets_str,
            "-Q", "--yolo",
            "-q", prompt,
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=workdir or str(self.config.project_root),
        )
        return result.stdout if result.returncode == 0 else f"[ERROR] {result.stderr}"

    def _spawn_openrouter(self, cfg, prompt, toolsets, timeout, workdir):
        """OpenRouter spawn — VPN 代理 + A 账户 API key"""
        toolsets_str = ",".join(toolsets)
        proxy = cfg.get("proxy", "http://127.0.0.1:7890")

        cmd = [
            "hermes", "chat",
            "--provider", "openrouter",
            "--model", cfg["model"],
            "--toolsets", toolsets_str,
            "-Q", "--yolo",
            "-q", prompt,
        ]
        env = os.environ.copy()
        env["HTTPS_PROXY"] = proxy
        env["HTTP_PROXY"] = proxy

        # 从 .env 加载 OpenRouter A 账户 key
        env_file = Path.home() / ".hermes" / ".env"
        if env_file.exists():
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("OPENROUTER_A_API_KEY="):
                        key = line.split("=", 1)[1].strip().strip('"').strip("'")
                        env["OPENROUTER_API_KEY"] = key
                        break

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=workdir or str(self.config.project_root),
            env=env,
        )
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
