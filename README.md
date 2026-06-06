# 星海理事会 (Star Council)

<p align="center">
  <img src="https://img.shields.io/badge/python-3.10+-blue" alt="Python">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License">
  <img src="https://img.shields.io/badge/Hermes-Agent-orange" alt="Hermes">
</p>

AI 驱动的学术论文多 Agent 协作写作系统。5 个专业理事围绕你的论文进行多轮讨论——各自独立发言、互相质疑、跑代码搜论文、最终形成可执行的行动方案。

> **你在主席位。他们干活，你决策。**

## 怎么工作

```
         ┌─────────────┐
         │   主席（你）  │  ← 关键节点介入决策
         └──────┬──────┘
    ┌───────────┼───────────┐
    │           │           │
┌───▼───┐ ┌────▼────┐ ┌───▼───┐
│ 文献   │ │ 魔鬼    │ │ 文字   │
│ 理事   │ │ 代言人  │ │ 理事   │
└───┬───┘ └────┬────┘ └───┬───┘
    │           │           │
    └───────────┼───────────┘
    ┌───────────┼───────────┐
┌───▼───┐ ┌────▼────┐
│ 架构   │ │ 实验    │
│ 理事   │ │ 理事    │
└───────┘ └─────────┘
```

每位理事是一个**独立的 Hermes Agent 子进程**，有自己的模型、工具链（terminal、web_search、file 等）。讨论时发言，散会后自主干活。

## 理事阵容

| 理事 | 角色 | 默认模型 | 会干什么 |
|---|---|---|---|
| 架构理事 | 方法设计、创新性、理论正确性 | Claude Opus 4 | 设计架构、推导公式、论证 novelty |
| 实验理事 | 实验方案、统计严谨性、可行性 | DeepSeek V4 Pro | 写实验计划、算样本量、找 benchmark |
| 文献理事 | 领域地图、相关工作、前沿追踪 | DeepSeek V4 Pro | 搜论文、画对比表格、找研究空白 |
| 文字理事 | 叙事逻辑、写作质量、venue 适配 | DeepSeek V4 Pro | 润色段落、调整结构、适配模板 |
| 魔鬼代言人 | 挑刺、模拟 reviewer、找漏洞 | DeepSeek V4 Pro | 每 3 轮强制发言，质疑所有宣称 |

## 会议阶段

所有理事全程参与，但不同阶段权重不同：

| 阶段 | 做什么 | 主导 |
|---|---|---|
| `ideation` | Idea 探索和评判 | 文献 + 架构 |
| `design` | 方法设计 | 架构 + 实验 |
| `experiment` | 实验规划 | 实验 |
| `writing` | 论文写作 | 文字 |
| `revision` | 修改 / Rebuttal | 全员均衡 |

## 快速开始

### 前提条件

- Python 3.10+
- [Hermes Agent](https://github.com/nousresearch/hermes-agent) 已安装
- DeepSeek API key（所有理事默认用 DeepSeek）
- OpenRouter API key（仅架构理事用 Claude Opus 4，可选）

### 安装

```bash
git clone https://github.com/Newtonian-No/star-council.git
cd star-council
bash bin/setup.sh
```

初始化脚本会：创建 venv → 安装依赖（pyyaml, gitpython, filelock）→ 验证。

### 第一次会议

```bash
source .venv/bin/activate

# Idea 探索
python bin/council.py meet "my-paper" --stage ideation --topic "医学图像分割中的 Mamba 架构改进"

# 查看状态
python bin/council.py status "my-paper"

# 列出所有项目
python bin/council.py list
```

### 单理事测试

不想开完整会议？单独调一个理事出来聊聊：

```bash
source .venv/bin/activate
python src/councilor.py devil "评估这个 idea：用 Mixture of Experts 改进 UNet 跳跃连接"
```

## 配置

`config.yaml` 中自定义模型和权重：

```yaml
councilors:
  architect:
    provider: openrouter        # 架构理事默认走 OpenRouter
    model: anthropic/claude-opus-4
    proxy: "http://127.0.0.1:7890"  # 国内需要 VPN
  experiment:
    provider: deepseek          # 其余 4 位默认走 DeepSeek 直连
    model: deepseek-v4-pro
```

**国内网络注意**：架构理事走 OpenRouter 需要代理。不翻墙的话，把 architect 也改成 deepseek 就行：

```yaml
councilors:
  architect:
    provider: deepseek
    model: deepseek-v4-pro
```

## 架构

### 消息总线

文件系统消息总线（`src/message_bus.py`），每轮讨论写入独立文件，用 `filelock` 保护并发写。下游理事读取最近 N 轮作为发言上下文。

### 会议流程

```
Round 1: 文献理事做领域概述（单发言人）
         ↓
Round 2-N: 按权重排序轮流发言 + 魔鬼代言人每3轮强制介入
         ↓
收敛检测: 发言长度显著缩短 → 会议结束
         ↓
自动 git commit（push GitHub）
```

### 收敛检测

简单但实用：最近两轮总发言字数显著减少 → 讨论趋于收敛，自动结束。

## 项目结构

```
star-council/
├── config.yaml         # 模型配置、权重、git 设置
├── bin/
│   ├── council.py      # CLI 入口（meet / status / list）
│   └── setup.sh        # 一键初始化
├── src/
│   ├── councilor.py    # 理事 spawn 引擎（单例 + 批量）
│   ├── message_bus.py  # 文件系统消息总线
│   └── councilors/     # 理事特化接口（预留扩展）
├── prompts/            # 5 理事 persona 定义
├── sessions/           # 会议记录（git 管理，自动归档）
├── templates/          # 论文模板（预留）
└── docs/               # 文档
```

## 使用 Hermes Skill 调度

如果你用 Hermes Agent，集成一行搞定：

```python
# 在你的 Agent 里唤起星海理事会
terminal("cd ~/star-council && source .venv/bin/activate && python bin/council.py meet 'my-paper' --stage ideation --topic '...'")
```

或直接装 Hermes skill（[skill 文件](./../hermes/skills/star-council/SKILL.md)），让 Agent 自动按阶段权重调度理事。

## 实际案例

系统在 GFR（肾小球滤过率自动估算）论文的 idea 评审中已验证：

- 文献理事搜到了 5 篇最新的 Mamba 医学图像分割工作，指出 Cross-scan 在核医学图像上的局限性
- 架构理事建议 UNet3+ + Deformable Convolution 作为 backbone，给出了消融实验设计
- 魔鬼代言人质疑了数据集规模、临床指标选择和与临床金标准的对比方案
- 5 轮后收敛，形成可执行实验方案

## 常见问题

**Q: 不开 VPN 能用吗？**  
把 config.yaml 里 architect 的 provider 改成 deepseek 就行，全部走国内直连。

**Q: 需要什么 API key？**  
DeepSeek API key 必须。如果你不换模型，OpenRouter 只需要给架构理事用。

**Q: 一次会议多长时间？**  
取决于轮数和赞助商网络。5 轮会议大约 5-10 分钟。

**Q: 会议记录在哪儿？**  
`sessions/<项目名>/meetings/<时间戳>/` 下，每个理事发言都是独立 .md 文件，有完整 transcript。

## 依赖

- Python 3.10+
- [Hermes Agent](https://github.com/nousresearch/hermes-agent)
- DeepSeek API（直连）
- OpenRouter API（架构理事，可选）

## 贡献

欢迎开 Issue 和 PR。方向建议：

- 更多理事（统计理事、可视化理事）
- Docker 化部署
- Web UI
- 自动生成 Beamer 答辩 slides

## License

MIT
