"""MiniCode Agent —— CLI 入口"""
import sys
import os
from pathlib import Path

# 确保项目根目录在 sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
from src.agent import MiniCodeAgent


def main():
    # 从项目根目录加载 .env（而不是从当前工作目录）
    project_root = Path(__file__).resolve().parent.parent
    env_path = project_root / ".env"
    load_dotenv(env_path)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("错误: 未设置 OPENAI_API_KEY，请检查 .env 文件")
        print("cp .env.example .env 并填入你的 API Key")
        sys.exit(1)

    agent = MiniCodeAgent()
    agent.chat()


if __name__ == "__main__":
    main()
