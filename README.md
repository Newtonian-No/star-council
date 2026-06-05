# 星海理事会 (Star Council)

AI 驱动的学术论文多 Agent 协作写作系统。5 个专业理事围绕你的论文进行多轮讨论，各自独立发言、互相质疑、最终形成可执行的行动方案。

## 理事阵容

| 理事 | 角色 | 默认模型 |
|---|---|---|
| 架构理事 | 方法设计、技术创新性、架构论证 | Claude Opus 4 |
| 实验理事 | 实验方案、统计严谨性、计算可行性 | DeepSeek V4 Pro |
| 文献理事 | 领域地图、相关工作、前沿追踪 | DeepSeek V4 Pro |
| 文字理事 | 叙事逻辑、写作质量、venue 适配 | DeepSeek V4 Pro |
| 魔鬼代言人 | 全程挑刺、模拟 reviewer、找逻辑漏洞 | DeepSeek V4 Pro |

每个理事 = 独立 Hermes Agent 子进程，有完整工具链（terminal、web_search、file 等）。讨论时说话，散会后干活。

## 设计理念

- **理事即执行者**：不存在"动口不动手"的分工
- **全程在线，权重不同**：所有理事在任何阶段都参与，只是发言权重随阶段变化
- **主席决策制**：用户是主席，关键决策点介入
- **自我归档**：每轮讨论自动 git commit，完整记录可追溯

## 快速开始

```bash
# 1. 环境初始化
bash bin/setup.sh

# 2. 召开第一次会议
source .venv/bin/activate
python bin/council.py meet "my-paper" --stage ideation --topic "讨论核心创新点"

# 3. 查看状态
python bin/council.py status "my-paper"
```

## 会议阶段

| 阶段 | 说明 | 主导理事 |
|---|---|---|
| `ideation` | Idea 探索和评判 | 文献 + 架构 |
| `design` | 方法设计 | 架构 + 实验 |
| `experiment` | 实验规划 | 实验 |
| `writing` | 论文写作 | 文字 |
| `revision` | 修改/Rebuttal | 全员均衡 |

## 项目结构

```
star-council/
├── config.yaml          # 模型配置、权重、git 设置
├── bin/
│   ├── council.py       # CLI 入口
│   └── setup.sh         # 一键初始化
├── src/
│   ├── councilor.py     # 理事 spawn 引擎
│   └── message_bus.py   # 文件系统消息总线
├── prompts/             # 5 理事 persona 定义
├── sessions/            # 会议记录（每个项目独立目录）
└── docs/                # 文档
```

## 配置

`config.yaml` 中可自定义每个理事的模型、provider、toolsets：

```yaml
councilors:
  architect:
    provider: openrouter
    model: anthropic/claude-opus-4
  experiment:
    provider: deepseek
    model: deepseek-v4-pro
```

## 依赖

- Python 3.10+
- Hermes Agent
- DeepSeek API 或 OpenRouter API

## License

MIT
