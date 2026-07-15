"""测试 Skill 路由系统"""
import sys
import io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.skills import SkillRouter, SKILL_CATALOG


def test_catalog_has_four_skills():
    assert len(SKILL_CATALOG) == 4, f"期望 4 个 Skill，实际: {len(SKILL_CATALOG)}"


def test_router_code_reader():
    router = SkillRouter()
    skill, tools = router.route("帮我阅读这个文件")
    assert skill.name == "code_reader", f"期望 code_reader，实际: {skill.name}"


def test_router_code_writer():
    router = SkillRouter()
    skill, tools = router.route("帮我写一个排序函数")
    assert skill.name == "code_writer", f"期望 code_writer，实际: {skill.name}"


def test_router_debugger():
    router = SkillRouter()
    skill, tools = router.route("这个bug怎么调试，一直报错")
    assert skill.name == "debugger", f"期望 debugger，实际: {skill.name}"


def test_router_researcher():
    router = SkillRouter()
    skill, tools = router.route("怎么搜索 Python 多线程教程")
    assert skill.name == "researcher", f"期望 researcher，实际: {skill.name}"


def test_router_defaults_to_code_reader():
    router = SkillRouter()
    skill, tools = router.route("你好")  # 无关键词匹配
    assert skill.name == "code_reader"


def test_router_returns_tools():
    router = SkillRouter()
    skill, tools = router.route("读取 main.py")
    assert len(tools) > 0
    tool_names = [t.name for t in tools]
    assert "read_file" in tool_names


def test_stage1_recall_scores():
    router = SkillRouter()
    # "写代码" 包含 "写" 和 "代码" 两个关键词 -> code_writer 得分最高
    candidates = router.stage1_recall("帮我查看项目结构")
    assert len(candidates) > 0
    assert candidates[0].name == "code_reader"


if __name__ == "__main__":
    test_catalog_has_four_skills()
    test_router_code_reader()
    test_router_code_writer()
    test_router_debugger()
    test_router_researcher()
    test_router_defaults_to_code_reader()
    test_router_returns_tools()
    test_stage1_recall_scores()
    print("test_skills: 全部通过")
