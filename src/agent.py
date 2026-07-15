"""Agent 核心循环 —— ReAct 模式的 Query Loop"""
import json
import os
from openai import OpenAI
from .tools import ToolDef, BUILTIN_TOOLS, get_tool_by_name
from .skills import SkillRouter, SkillDef
from .memory import SessionMemory, ExperienceMemory
from .security import (
    sanitize_command, validate_input, validate_path,
    check_file_write_safety, get_safe_cwd, SecurityError,
)

MAX_ITERATIONS = 15  # 单次任务最大工具调用轮数


class MiniCodeAgent:
    """MiniCode AI Coding Agent"""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        max_turns: int = 20,
    ):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "sk-placeholder")
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com")
        self.model = model or os.getenv("LLM_MODEL", "deepseek-chat")

        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        self.router = SkillRouter()
        self.memory = SessionMemory(max_turns=max_turns)
        self.experience = ExperienceMemory()
        self.all_tools = BUILTIN_TOOLS

    def _build_system_prompt(self, skill) -> str:
        """组装系统提示词"""
        parts = [
            skill.prompt,
            "你是一个 AI 编程助手，可以使用工具来完成用户的任务。",
            "当前工作目录: " + get_safe_cwd(),
            "遇到不确定的事情，先用 read_file 或 list_dir 了解上下文。",
            "修改代码前，先 read_file 阅读文件。",
            "回答简洁，用中文。",
        ]
        # 注入经验记忆
        exp_text = self.experience.get_for_context()
        if exp_text:
            parts.append(exp_text)
        return "\n".join(parts)

    def _execute_tool(self, name: str, args: dict) -> str:
        """执行工具调用，包装安全检查"""
        try:
            if name == "read_file":
                path = validate_path(args["filepath"])
                tool = get_tool_by_name(name)
                return tool.handler(str(path))

            elif name == "write_file":
                path = check_file_write_safety(args["filepath"])
                tool = get_tool_by_name(name)
                return tool.handler(str(path), args["content"])

            elif name == "run_shell":
                cmd = sanitize_command(args["command"])
                tool = get_tool_by_name(name)
                return tool.handler(cmd)

            else:
                tool = get_tool_by_name(name)
                if tool:
                    return tool.handler(**args)
                return f"未知工具: {name}"

        except SecurityError as e:
            return f"安全阻止: {e}"
        except Exception as e:
            return f"工具执行失败: {e}"

    def run(self, user_input: str) -> str:
        """执行一次用户请求，返回最终回答"""
        user_input = user_input.strip()
        if not user_input:
            return "请输入你的需求。"

        # 安全检查
        try:
            user_input = validate_input(user_input)
        except SecurityError as e:
            return f"输入被拒绝: {e}"

        # 存入记忆
        self.memory.add("user", user_input)

        # Skill 路由
        skill, skill_tools = self.router.route(user_input)
        available_tools = skill_tools or self.all_tools

        # 获取记忆上下文
        memory_context = self.memory.get_context()

        # 构建消息列表
        messages = [
            {"role": "system", "content": self._build_system_prompt(skill)},
        ]
        messages.extend(memory_context)

        # 将可用工具转为 OpenAI 格式
        openai_tools = [t.to_openai_tool() for t in available_tools]

        iteration = 0
        while iteration < MAX_ITERATIONS:
            iteration += 1

            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=openai_tools if openai_tools else None,
                    temperature=0.3,
                    max_tokens=2048,
                )
            except Exception as e:
                return f"LLM 调用失败: {e}"

            choice = response.choices[0]
            msg = choice.message

            # 没有工具调用 → 最终回答
            if not msg.tool_calls:
                answer = msg.content or ""
                self.memory.add("assistant", answer)

                # 自动沉淀经验
                self._maybe_record_experience(user_input, answer)
                return answer

            # 有工具调用 → 执行
            # 将 assistant 消息加入历史
            messages.append({
                "role": "assistant",
                "content": msg.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in msg.tool_calls
                ],
            })

            for tc in msg.tool_calls:
                tool_name = tc.function.name
                try:
                    tool_args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    tool_args = {}

                # 记录工具调用到记忆
                self.memory.add("tool", f"[调用] {tool_name}: {json.dumps(tool_args, ensure_ascii=False)}")

                result = self._execute_tool(tool_name, tool_args)
                self.memory.add("tool", f"[结果] {result[:500]}")

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                })

        # 超出最大迭代
        return "任务未完成，已超出最大推理轮数。请尝试拆分任务。"

    def _maybe_record_experience(self, user_input: str, answer: str):
        """自动经验沉淀：简单判断是否有值得记录的教训"""
        if len(user_input) < 20:
            return
        # 如果回答太短（可能是简单查询），不记录
        if len(answer) < 50:
            return
        # 简单记录任务 + 简要结果
        lesson = answer[:100].replace("\n", " ")
        self.experience.add(
            task=user_input[:80],
            outcome="completed",
            lesson=lesson,
        )

    def chat(self):
        """交互式 REPL"""
        print(f"\n  MiniCode Agent 已启动")
        print(f"  模型: {self.model}")
        print(f"  输入 /exit 退出, /clear 清空记忆\n")

        while True:
            try:
                user_input = input("你> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n  再见！")
                break

            if not user_input:
                continue

            if user_input.lower() in ("/exit", "/quit"):
                print("  再见！")
                break

            if user_input.lower() == "/clear":
                self.memory.messages.clear()
                self.memory.key_facts.clear()
                print("  记忆已清空。")
                continue

            if user_input.lower() == "/summary":
                print(f"  当前对话轮数: {len(self.memory.messages)}")
                print(f"  关键信息: {len(self.memory.key_facts)} 条")
                continue

            print()  # 空行
            response = self.run(user_input)
            print(f"\nAgent> {response}\n")
