"""Tool 系统 —— Agent 的工具定义、注册、执行"""
import os
import subprocess
from pathlib import Path
from typing import Callable
from pydantic import BaseModel


class ToolDef(BaseModel):
    """工具定义（兼容 OpenAI Function Calling 格式）"""
    name: str
    description: str
    parameters: dict  # JSON Schema
    handler: Callable  # 实际执行的函数（不参与序列化）

    class Config:
        arbitrary_types_allowed = True

    def to_openai_tool(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


# ═══════════════════════════════════════════════════════════════
# 内置工具实现
# ═══════════════════════════════════════════════════════════════

def tool_read_file(filepath: str) -> str:
    """读取文件内容"""
    path = Path(filepath).expanduser()
    if not path.exists():
        return f"错误: 文件不存在 - {filepath}"
    try:
        return path.read_text(encoding="utf-8")
    except Exception as e:
        return f"错误: {e}"


def tool_write_file(filepath: str, content: str) -> str:
    """写入文件"""
    path = Path(filepath).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.write_text(content, encoding="utf-8")
        return f"已写入: {filepath} ({len(content)} 字符)"
    except Exception as e:
        return f"错误: {e}"


def tool_list_dir(directory: str) -> str:
    """列出目录内容"""
    path = Path(directory).expanduser()
    if not path.exists():
        return f"错误: 目录不存在 - {directory}"
    items = []
    for item in sorted(path.iterdir()):
        prefix = "[D]" if item.is_dir() else "[F]"
        items.append(f"{prefix} {item.name}")
    return "\n".join(items) if items else "(空目录)"


def tool_run_shell(command: str) -> str:
    """执行 Shell 命令（受限）"""
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=30,
            cwd=os.getcwd(),
        )
        output = result.stdout.strip() or result.stderr.strip()
        return output[:2000]  # 限制输出长度
    except subprocess.TimeoutExpired:
        return "错误: 命令执行超时（30秒）"
    except Exception as e:
        return f"错误: {e}"


def tool_web_search(query: str) -> str:
    """模拟网络搜索（实际使用时替换为真实搜索 API）"""
    return (
        f"[模拟搜索] 查询: {query}\n"
        "提示: 请配置 SEARCH_API_KEY 以启用真实搜索。\n"
        "可用的搜索 API: Bing Search, SerpAPI, Tavily"
    )


# ═══════════════════════════════════════════════════════════════
# 工具注册表
# ═══════════════════════════════════════════════════════════════

BUILTIN_TOOLS = [
    ToolDef(
        name="read_file",
        description="读取指定文件的内容。用于查看代码、配置文件等。",
        parameters={
            "type": "object",
            "properties": {
                "filepath": {"type": "string", "description": "文件路径"}
            },
            "required": ["filepath"],
        },
        handler=tool_read_file,
    ),
    ToolDef(
        name="write_file",
        description="将内容写入指定文件。用于创建或修改代码文件。",
        parameters={
            "type": "object",
            "properties": {
                "filepath": {"type": "string", "description": "文件路径"},
                "content": {"type": "string", "description": "要写入的内容"},
            },
            "required": ["filepath", "content"],
        },
        handler=tool_write_file,
    ),
    ToolDef(
        name="list_dir",
        description="列出目录中的文件和子目录。用于浏览项目结构。",
        parameters={
            "type": "object",
            "properties": {
                "directory": {"type": "string", "description": "目录路径"}
            },
            "required": ["directory"],
        },
        handler=tool_list_dir,
    ),
    ToolDef(
        name="run_shell",
        description="执行 Shell 命令。用于运行测试、安装依赖、构建项目等。",
        parameters={
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "要执行的命令"}
            },
            "required": ["command"],
        },
        handler=tool_run_shell,
    ),
    ToolDef(
        name="web_search",
        description="搜索互联网获取信息。用于查找文档、解决方案等。",
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "搜索关键词"}
            },
            "required": ["query"],
        },
        handler=tool_web_search,
    ),
]


def get_tool_by_name(name: str) -> ToolDef | None:
    for t in BUILTIN_TOOLS:
        if t.name == name:
            return t
    return None
