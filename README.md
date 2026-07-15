# MiniCode — AI Coding Agent

轻量级 AI 编程助手，基于 ReAct 模式的自主 Agent，支持工具调用、Skill 路由和记忆系统。

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## 架构

```
用户输入
   │
   ▼
┌──────────────┐
│  安全检查      │  ← 注入检测 / 路径校验 / 命令过滤
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  Skill 路由    │  ← 关键词召回 → 精排（扩展 LLM 精排）
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  ReAct 循环   │  ← Think → Act → Observe → Repeat
│  (最多15轮)    │     最多 15 轮，防止无限循环
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  工具执行      │  ← 读/写文件、Shell、搜索
│  + 安全检查    │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  记忆系统      │  ← 会话记忆（滚动窗口）+ 经验沉淀（持久化）
└──────────────┘
```

## 技术栈

| 层次 | 技术 |
|------|------|
| LLM | DeepSeek / OpenAI 兼容 API + Function Calling |
| Skill 路由 | 二阶段：关键词召回 + 规则精排 |
| 工具系统 | OpenAI Function Calling 格式，5 个内置工具 |
| 安全 | 提示注入检测 + 危险命令过滤 + 路径沙箱 |
| 记忆 | SessionMemory（滚动窗口）+ ExperienceMemory（JSON 持久化） |

## 内置 Skill

| Skill | 触发场景 | 可用工具 |
|-------|----------|----------|
| `code_reader` | 阅读/查看/理解代码 | read_file, list_dir |
| `code_writer` | 编写/修改/创建代码 | read_file, write_file, list_dir |
| `debugger` | 报错/调试/bug 排查 | read_file, run_shell, list_dir |
| `researcher` | 搜索/学习技术问题 | web_search, read_file |

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置
cp .env.example .env
# 编辑 .env，填入 OPENAI_API_KEY

# 3. 启动交互式 CLI
python -m src.main
```

## 内置指令

| 指令 | 说明 |
|------|------|
| `/exit` | 退出 |
| `/clear` | 清空会话记忆 |
| `/summary` | 查看记忆状态 |

## 安全机制

- 路径校验：只允许在项目目录和用户目录下操作，防止目录穿越
- 命令过滤：阻止 `rm -rf`、`chmod 777 /` 等危险命令
- 注入检测：识别 `ignore previous instructions`、`[system]` 等提示注入模式
- 文件保护：禁止覆盖 `.dll` `.exe` `.key` 等系统文件类型

## 项目结构

```
minicode/
├── src/
│   ├── agent.py      # Agent 核心循环（ReAct + Tool Calling）
│   ├── tools.py      # 工具定义、注册、执行
│   ├── skills.py     # Skill 路由（二阶段召回+精排）
│   ├── memory.py     # 会话记忆 + 经验沉淀
│   ├── security.py   # 安全检查（注入/路径/命令）
│   └── main.py       # CLI 入口
├── .env.example      # 环境变量模板
└── requirements.txt
```
