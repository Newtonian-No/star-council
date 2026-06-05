#!/usr/bin/env python3
"""
星海理事会 — 主 CLI

用法:
  python bin/council.py meet <project> --stage <stage> --topic "<topic>"
  python bin/council.py status <project>
  python bin/council.py list
"""

import sys
import os
from pathlib import Path

# 把 src 加入 path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from councilor import StarCouncilConfig, CouncilorSpawner, load_prompt
from message_bus import MessageBus, create_session


# === 会议流程 ===

def run_meeting(project: str, stage: str, topic: str):
    """运行一次理事会会议"""
    config = StarCouncilConfig()
    spawner = CouncilorSpawner(config)
    bus = create_session(project, stage, topic)

    weights = config.get_weights(stage)
    max_rounds = config.max_rounds

    print(f"\n{'='*60}")
    print(f"  星海理事会 — 第 1 次会议")
    print(f"  项目: {project}  阶段: {stage}")
    print(f"  议题: {topic}")
    print(f"{'='*60}\n")

    # 开场：文献理事做领域概述
    print("[Round 1] 文献理事 做领域概述...")
    literature_prompt = _build_prompt("literature", bus, stage, f"请对以下议题做领域概述：{topic}\n\n介绍相关领域的现状、主要方法、关键挑战和研究空白。")
    response = spawner.spawn("literature", literature_prompt)
    bus.post(1, "literature", response)
    print(f"  → 文献理事发言 ({len(response)} 字)\n")

    for round_num in range(2, max_rounds + 1):
        # 按权重排序发言人
        speaker_order = _get_speaker_order(weights, round_num)

        for speaker in speaker_order:
            print(f"[Round {round_num}] {speaker} 发言中...")

            context = bus.get_context(last_n_rounds=4)
            prompt = _build_prompt(speaker, bus, stage,
                f"请基于以上讨论发表你的观点。当前议题：{topic}\n\n"
                f"如果你同意前面的观点，可以补充证据或深化分析。"
                f"如果你不同意，请明确指出分歧并说明理由。")

            response = spawner.spawn(speaker, prompt)
            bus.post(round_num, speaker, response)
            print(f"  → {speaker} 发言 ({len(response)} 字)")

            # 每轮结束检查是否要暂停给用户
            if round_num % 3 == 0:
                print(f"  ⏸ Round {round_num} 完成，等待主席决策...")
                # 用户介入点：实际部署时通过 clarify 实现
                # MVP 阶段自动继续
                break

        # 收敛检查
        if _check_convergence(bus, round_num):
            print(f"\n✅ 讨论在第 {round_num} 轮收敛")
            break

    # 会议结束
    print(f"\n{'='*60}")
    print(f"  会议结束。记录保存在：{bus.session_dir}")
    print(f"{'='*60}")

    bus.save_metadata({**bus.load_metadata(), "status": "completed", "rounds": bus.get_last_round()})

    # Git 自动提交
    _auto_commit(project, bus.get_last_round(), topic)

    return bus


def _get_speaker_order(weights: dict, round_num: int) -> list[str]:
    """确定发言顺序：权重高的先发言，魔鬼代言人每3轮或最后发言"""
    sorted_councilors = sorted(weights.items(), key=lambda x: x[1], reverse=True)
    order = [c[0] for c in sorted_councilors if c[0] != "devil"]

    # 魔鬼代言人在第3轮、第6轮、第9轮...强制发言
    if round_num % 3 == 0 and round_num > 0:
        order.append("devil")
    elif len(order) >= 4:
        order.append("devil")  # 人多的轮次也让魔鬼发言

    return order


def _build_prompt(councilor: str, bus: MessageBus, stage: str, task: str) -> str:
    """构建发给理事的完整 prompt"""
    system = load_prompt(councilor)
    context = bus.get_context(last_n_rounds=4)
    stage_names = {
        "ideation": "idea探索",
        "design": "方法设计",
        "experiment": "实验规划",
        "writing": "论文写作",
        "revision": "修改/Rebuttal",
    }
    return f"{system}\n\n---\n\n## 讨论上下文（最近几轮）\n\n{context}\n\n---\n\n## 当前阶段：{stage_names.get(stage, stage)}\n\n{task}\n\n请以{councilor}的身份发言。用中文讨论，技术术语保留英文。"


def _check_convergence(bus: MessageBus, round_num: int) -> bool:
    """简单的收敛检查：最后两轮内容高度相似则收敛"""
    if round_num < 3:
        return False

    r1 = bus.get_round_messages(round_num)
    r0 = bus.get_round_messages(round_num - 1)
    if not r1 or not r0:
        return False

    # 简单策略：最后两轮的发言字数都显著减少 → 趋于收敛
    len_r1 = sum(len(m) for m in r1)
    len_r0 = sum(len(m) for m in r0)
    if len_r1 < len_r0 * 0.5 and len_r1 < 1000:
        return True
    return False


def _auto_commit(project: str, rounds: int, topic: str):
    """自动 git commit"""
    try:
        from git import Repo
        repo_root = Path(__file__).parent.parent
        repo = Repo(str(repo_root))
        repo.git.add("-A")
        repo.index.commit(f"meeting: {project} — {topic} ({rounds} rounds)")
        # 尝试 push
        try:
            repo.git.push("origin", "main")
        except Exception:
            pass  # push 失败不阻塞
    except Exception as e:
        print(f"  [git] commit skipped: {e}")


# === 状态查看 ===

def show_status(project: str):
    """查看项目状态"""
    sessions_dir = Path(__file__).parent.parent / "sessions" / project
    if not sessions_dir.exists():
        print(f"项目 {project} 尚无会议记录")
        return

    meetings_dir = sessions_dir / "meetings"
    meetings = sorted(meetings_dir.glob("*"), reverse=True)

    print(f"\n项目: {project}")
    print(f"会议数: {len(meetings)}")
    print()

    for m in meetings[:5]:
        meta_file = m / "metadata.json"
        if meta_file.exists():
            import json
            meta = json.loads(meta_file.read_text())
            status = meta.get("status", "?")
            rounds = meta.get("rounds", "?")
            topic = meta.get("topic", "?")[:50]
            print(f"  [{status}] {m.name} — {topic} ({rounds} 轮)")


# === CLI ===

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "meet":
        project = sys.argv[2] if len(sys.argv) > 2 else "default"
        stage = "ideation"
        topic = "无特定议题"
        for i, arg in enumerate(sys.argv):
            if arg == "--stage" and i + 1 < len(sys.argv):
                stage = sys.argv[i + 1]
            if arg == "--topic" and i + 1 < len(sys.argv):
                topic = sys.argv[i + 1]
        run_meeting(project, stage, topic)

    elif cmd == "status":
        project = sys.argv[2] if len(sys.argv) > 2 else "default"
        show_status(project)

    elif cmd == "list":
        sessions_dir = Path(__file__).parent.parent / "sessions"
        if sessions_dir.exists():
            for p in sorted(sessions_dir.iterdir()):
                if p.is_dir():
                    print(f"  {p.name}")
        else:
            print("无项目")

    else:
        print(f"未知命令: {cmd}")
        print(__doc__)
