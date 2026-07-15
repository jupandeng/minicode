"""测试工具系统"""
import sys
import io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.tools import (
    BUILTIN_TOOLS, get_tool_by_name,
    tool_read_file, tool_write_file, tool_list_dir,
)


def test_builtin_tools_count():
    assert len(BUILTIN_TOOLS) == 5, f"期望 5 个工具，实际: {len(BUILTIN_TOOLS)}"


def test_all_tools_have_names():
    for t in BUILTIN_TOOLS:
        assert t.name, f"工具有空名称"
        assert t.description, f"工具 {t.name} 缺少描述"


def test_get_tool_by_name():
    tool = get_tool_by_name("read_file")
    assert tool is not None
    assert tool.name == "read_file"

    assert get_tool_by_name("nonexistent") is None


def test_to_openai_tool_format():
    tool = get_tool_by_name("read_file")
    result = tool.to_openai_tool()
    assert result["type"] == "function"
    assert result["function"]["name"] == "read_file"
    assert "parameters" in result["function"]


def test_read_file_not_found():
    result = tool_read_file("/nonexistent/path/12345.txt")
    assert "错误" in result or "不存在" in result


def test_read_file_returns_content():
    # 读取一个真实存在的文件
    result = tool_read_file(str(Path(__file__).resolve()))
    assert len(result) > 0
    assert "test_tools" in result  # 文件内容应包含自身函数名


def test_list_dir_returns_items():
    result = tool_list_dir(str(Path(__file__).resolve().parent.parent / "src"))
    assert ".py" in result or "agent" in result


def test_write_and_read_roundtrip(tmp_path=None):
    import tempfile, os
    if tmp_path is None:
        tmp_path = Path(tempfile.mkdtemp()) / "test.txt"
    path = str(tmp_path)
    tool_write_file(path, "Hello MiniCode")
    result = tool_read_file(path)
    assert "Hello MiniCode" in result
    os.remove(path)


if __name__ == "__main__":
    test_builtin_tools_count()
    test_all_tools_have_names()
    test_get_tool_by_name()
    test_to_openai_tool_format()
    test_read_file_not_found()
    test_read_file_returns_content()
    test_list_dir_returns_items()
    test_write_and_read_roundtrip()
    print("test_tools: 全部通过")
