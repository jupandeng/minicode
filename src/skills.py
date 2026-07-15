"""Skill 路由系统 —— 意图识别 + 二阶段召回与精排"""
from pydantic import BaseModel
from .tools import ToolDef, BUILTIN_TOOLS


class SkillDef(BaseModel):
    """Skill 定义"""
    name: str
    description: str
    triggers: list[str]       # 触发关键词
    tools: list[str]           # 该 Skill 可用的工具名
    prompt: str = ""           # Skill 专属系统提示


# ═══════════════════════════════════════════════════════════════
# 内置 Skill 目录
# ═══════════════════════════════════════════════════════════════

SKILL_CATALOG = [
    SkillDef(
        name="code_reader",
        description="阅读和理解代码",
        triggers=["读取", "查看", "阅读", "看看", "代码", "文件", "项目结构"],
        tools=["read_file", "list_dir"],
        prompt="你是代码阅读助手。先浏览项目结构，再阅读相关文件，最后给出分析。",
    ),
    SkillDef(
        name="code_writer",
        description="编写和修改代码",
        triggers=["写", "创建", "修改", "改", "新建", "实现", "添加", "加", "修复", "fix"],
        tools=["read_file", "write_file", "list_dir"],
        prompt="你是代码编写助手。先阅读现有代码了解上下文，再编写修改，确保代码风格一致。",
    ),
    SkillDef(
        name="debugger",
        description="调试和修复错误",
        triggers=["报错", "错误", "bug", "调试", "为什么", "不行", "没反应", "出错"],
        tools=["read_file", "run_shell", "list_dir"],
        prompt="你是调试助手。先复现错误，分析根因，再提出修复方案。",
    ),
    SkillDef(
        name="researcher",
        description="搜索和研究技术问题",
        triggers=["搜索", "查", "怎么", "如何", "什么是", "介绍", "教程"],
        tools=["web_search", "read_file"],
        prompt="你是技术研究助手。先搜索相关资料，整理信息后给出清晰答案。",
    ),
]


# ═══════════════════════════════════════════════════════════════
# 二阶段路由
# ═══════════════════════════════════════════════════════════════

class SkillRouter:
    """二阶段 Skill 路由：粗召回 → 精排"""

    def __init__(self, skills: list[SkillDef] | None = None):
        self.skills = skills or SKILL_CATALOG

    def stage1_recall(self, user_input: str) -> list[SkillDef]:
        """阶段一：关键词粗召回"""
        scored = []
        for skill in self.skills:
            score = sum(
                1 for kw in skill.triggers
                if kw.lower() in user_input.lower()
            )
            if score > 0:
                scored.append((score, skill))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [s for _, s in scored]

    def stage2_rerank(self, user_input: str, candidates: list[SkillDef]) -> SkillDef:
        """阶段二：LLM 精排（简化版：用规则代替 LLM 调用以降低延迟）

        实际生产环境可替换为 LLM 打分：
        - 将用户输入 + 候选 Skill 描述发给 LLM
        - LLM 选出最合适的 Skill
        - 成本和延迟换取更高的准确率
        """
        if not candidates:
            return SKILL_CATALOG[0]  # 默认 code_reader
        return candidates[0]  # 当前用规则排序结果

    def route(self, user_input: str) -> tuple[SkillDef, list[ToolDef]]:
        """路由主流程：返回匹配的 Skill 及其可用工具"""
        candidates = self.stage1_recall(user_input)
        best_skill = self.stage2_rerank(user_input, candidates)

        # 获取该 Skill 的可用工具
        tools = []
        for name in best_skill.tools:
            from .tools import get_tool_by_name
            tool = get_tool_by_name(name)
            if tool:
                tools.append(tool)

        return best_skill, tools
