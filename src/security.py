"""安全模块 —— 命令过滤 + 路径校验 + 注入检测"""
import os
import re
from pathlib import Path

# 危险命令模式（阻止执行）
BLOCKED_PATTERNS = [
    r"\brm\s+-rf\b",           # 递归删除
    r"\bdd\s+if=",              # 磁盘写入
    r">\s*/dev/sd",             # 写入块设备
    r"\bmkfs\.",                # 格式化
    r":\(\)\s*\{\s*:\|:&\s*\};:",  # fork 炸弹
    r"\bchmod\s+777\s+/",       # 权限全开系统目录
    r"\bwget\b.*\|\s*(ba)?sh",  # 管道执行远程脚本
    r"\bcurl\b.*\|\s*(ba)?sh",
]

# 允许的工作目录
ALLOWED_PATHS = [
    Path.cwd(),
    Path.home(),
    Path.home() / "Desktop",
    Path.home() / "Documents",
    Path("D:/projects"),
    Path("D:/"),
]


class SecurityError(Exception):
    """安全违规异常"""


def sanitize_command(command: str) -> str:
    """检查命令安全性，通过则返回原命令"""
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            raise SecurityError(f"危险命令被阻止: 匹配模式 '{pattern}'")
    return command


def validate_path(filepath: str) -> Path:
    """校验路径合法性，防止目录穿越"""
    path = Path(filepath).expanduser().resolve()

    # 检查是否在允许的目录范围内
    for allowed in ALLOWED_PATHS:
        try:
            path.relative_to(allowed.resolve())
            return path
        except ValueError:
            continue

    raise SecurityError(f"路径访问被拒绝: {filepath}")


def detect_injection(text: str) -> bool:
    """检测提示注入攻击"""
    patterns = [
        r"(ignore|forget|disregard)\s+(all\s+)?(previous|above|earlier)\s+(instructions?|prompts?)",
        r"you\s+are\s+now\s+(a\s+)?\w+\s+(bot|assistant|agent)",
        r"<\|im_start\|>",       # LLM token 注入
        r"<\|im_end\|>",
        r"\[system\]\(",          # 角色伪装
        r"\[INST\]",              # Mistral/Llama 指令注入
        r"<<SYS>>",              # Llama 系统提示注入
    ]
    for pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


def validate_input(user_input: str) -> str:
    """用户输入安全检查：注入检测 + 长度限制"""
    if len(user_input) > 8000:
        raise SecurityError("输入过长（最大 8000 字符）")

    if detect_injection(user_input):
        raise SecurityError("检测到提示注入攻击")

    return user_input


def check_file_write_safety(filepath: str) -> Path:
    """写文件前检查：路径合法 + 不会覆盖关键系统文件"""
    path = validate_path(filepath)

    dangerous_exts = {".dll", ".so", ".dylib", ".exe", ".sys", ".key", ".pem"}
    if path.suffix.lower() in dangerous_exts:
        raise SecurityError(f"不允许写入此类型文件: {path.suffix}")

    # 禁止覆盖 /etc /System32 等关键目录
    dangerous_dirs = ["/etc", "/System32", "/boot", "C:\\Windows", "C:\\Windows\\System32"]
    for d in dangerous_dirs:
        try:
            path.resolve().relative_to(Path(d).resolve())
            raise SecurityError(f"禁止写入系统目录: {d}")
        except ValueError:
            continue

    return path


def get_safe_cwd() -> str:
    """返回安全的当前工作目录"""
    cwd = Path.cwd().resolve()
    for allowed in ALLOWED_PATHS:
        try:
            cwd.relative_to(allowed.resolve())
            return str(cwd)
        except ValueError:
            continue
    return str(Path.home())
