"""
星海理事会 — 文件系统消息总线

每次理事发言 = 一个消息文件。所有消息按轮次组织，
汇总到 transcript.md。下游理事读取最近 N 轮作为上下文。
"""

import os
from datetime import datetime, timezone
from pathlib import Path
from filelock import FileLock
from typing import Optional


class MessageBus:
    """文件系统消息总线"""

    def __init__(self, session_dir: str):
        self.session_dir = Path(session_dir)
        self.rounds_dir = self.session_dir / "rounds"
        self.transcript_file = self.session_dir / "transcript.md"
        self._ensure_dirs()

    def _ensure_dirs(self):
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.rounds_dir.mkdir(exist_ok=True)
        self.transcript_file.touch()

    # === 写入 ===

    def post(self, round_num: int, speaker: str, content: str):
        """发布一条消息"""
        timestamp = datetime.now(timezone.utc).isoformat()
        msg_id = f"{round_num:03d}-{speaker}"
        msg_file = self.rounds_dir / f"{msg_id}.md"

        header = f"## {speaker} (Round {round_num}, {timestamp})\n\n"
        full_msg = header + content

        # 写入独立消息文件
        msg_file.write_text(full_msg, encoding="utf-8")

        # 追加到 transcript（文件锁保护并发写）
        lock = FileLock(str(self.transcript_file) + ".lock")
        with lock:
            with open(self.transcript_file, "a", encoding="utf-8") as f:
                f.write(f"\n---\n\n{full_msg}\n")

        return msg_id

    # === 读取 ===

    def get_context(self, last_n_rounds: int = 5) -> str:
        """获取最近 N 轮的讨论上下文，供理事阅读后发言"""
        if not self.transcript_file.exists():
            return "（暂无讨论记录）"

        text = self.transcript_file.read_text(encoding="utf-8")

        # 按轮次分割
        rounds = text.split("\n---\n")
        if len(rounds) <= last_n_rounds:
            return text.strip()

        return "\n---\n".join(rounds[-last_n_rounds:]).strip()

    def get_round_messages(self, round_num: int) -> list[str]:
        """获取某一轮的所有消息"""
        prefix = f"{round_num:03d}-"
        msgs = []
        for f in sorted(self.rounds_dir.glob(f"{prefix}*.md")):
            msgs.append(f.read_text(encoding="utf-8"))
        return msgs

    def list_rounds(self) -> list[int]:
        """列出所有轮次编号"""
        rounds = set()
        for f in self.rounds_dir.glob("*.md"):
            try:
                r = int(f.stem.split("-")[0])
                rounds.add(r)
            except ValueError:
                pass
        return sorted(rounds)

    def get_last_round(self) -> int:
        rounds = self.list_rounds()
        return rounds[-1] if rounds else 0

    def get_full_transcript(self) -> str:
        if self.transcript_file.exists():
            return self.transcript_file.read_text(encoding="utf-8")
        return ""

    # === 元数据 ===

    def save_metadata(self, data: dict):
        """保存 session 元数据"""
        import json
        meta_file = self.session_dir / "metadata.json"
        meta_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def load_metadata(self) -> dict:
        import json
        meta_file = self.session_dir / "metadata.json"
        if meta_file.exists():
            return json.loads(meta_file.read_text(encoding="utf-8"))
        return {}


# === 便捷函数 ===

def create_session(project: str, stage: str, topic: str, base_dir: str = None) -> MessageBus:
    """创建新的理事会 session"""
    if base_dir is None:
        base_dir = str(Path(__file__).parent.parent / "sessions")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_dir = Path(base_dir) / project / "meetings" / timestamp
    mb = MessageBus(str(session_dir))

    mb.save_metadata({
        "project": project,
        "stage": stage,
        "topic": topic,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "active",
    })

    return mb


if __name__ == "__main__":
    # 快速测试
    import sys
    if len(sys.argv) < 2:
        print("Usage: python message_bus.py <project_name>")
        sys.exit(1)

    mb = create_session(sys.argv[1], "ideation", "测试消息总线")
    mb.post(1, "architect", "这是一条来自架构理事的测试消息。")
    mb.post(1, "experiment", "实验理事回复：架构方案可行，需要补充消融实验。")

    print(f"Session dir: {mb.session_dir}")
    print(f"Rounds: {mb.list_rounds()}")
    print(f"Context:\n{mb.get_context()}")
