"""记忆系统 —— 会话记忆 + 经验沉淀"""
import json
import time
from pathlib import Path
from collections import deque
from pydantic import BaseModel


class MemoryEntry(BaseModel):
    """单条记忆"""
    role: str          # user / assistant / tool / experience
    content: str
    timestamp: float = 0.0

    def __init__(self, **data):
        if "timestamp" not in data or data["timestamp"] == 0.0:
            data["timestamp"] = time.time()
        super().__init__(**data)


class SessionMemory:
    """会话级记忆：滚动窗口 + 关键信息保留"""

    def __init__(self, max_turns: int = 20):
        self.max_turns = max_turns
        self.messages: deque[MemoryEntry] = deque()
        self.key_facts: dict[str, str] = {}  # 关键信息持久存储

    def add(self, role: str, content: str):
        self.messages.append(MemoryEntry(role=role, content=content))
        self._trim()

    def _trim(self):
        """超出窗口时，先提炼关键信息再丢弃旧消息"""
        while len(self.messages) > self.max_turns * 2:
            old = self.messages.popleft()
            # 自动提取用户偏好
            if old.role == "user" and "记住" in old.content:
                self.key_facts[f"user_pref_{len(self.key_facts)}"] = old.content

    def get_context(self, max_tokens: int = 4000) -> list[dict]:
        """获取上下文消息列表（估算 token 限制）"""
        result = []
        chars = 0
        # 新消息在前，但需要反转给 LLM（按时间顺序）
        for msg in reversed(self.messages):
            msg_chars = len(msg.content)
            if chars + msg_chars > max_tokens * 2:
                break
            result.append({"role": msg.role, "content": msg.content})
            chars += msg_chars
        # 反转回时间顺序
        result.reverse()

        # 如果有用户偏好，注入到最前面
        if self.key_facts:
            facts_text = "用户偏好/关键信息:\n" + "\n".join(
                f"- {v}" for v in self.key_facts.values()
            )
            result.insert(0, {"role": "system", "content": facts_text})

        return result

    def summarize_and_forget(self, summary_prompt: str, llm) -> str:
        """压缩记忆：将历史消息压缩为摘要，释放空间"""
        if len(self.messages) < 10:
            return ""

        history = "\n".join(
            f"[{m.role}] {m.content[:200]}" for m in self.messages
        )
        try:
            response = llm.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": summary_prompt},
                    {"role": "user", "content": f"请总结以下对话的关键信息:\n{history}"},
                ],
                max_tokens=300,
                temperature=0.2,
            )
            summary = response.choices[0].message.content
        except Exception:
            summary = "（摘要生成失败）"

        # 清空旧消息，注入摘要
        self.messages.clear()
        self.messages.append(MemoryEntry(role="system", content=f"[摘要] {summary}"))
        return summary


class ExperienceMemory:
    """经验记忆：跨会话复用的知识沉淀（文件持久化）"""

    def __init__(self, file_path: str = "data/experiences.json"):
        self.file_path = Path(file_path)
        self.experiences: list[dict] = self._load()

    def _load(self) -> list[dict]:
        if self.file_path.exists():
            return json.loads(self.file_path.read_text("utf-8"))
        return []

    def _save(self):
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self.file_path.write_text(
            json.dumps(self.experiences, ensure_ascii=False, indent=2),
            "utf-8",
        )

    def add(self, task: str, outcome: str, lesson: str):
        """记录一次经验：任务 → 结果 → 经验教训"""
        entry = {
            "task": task,
            "outcome": outcome,
            "lesson": lesson,
            "timestamp": time.time(),
        }
        self.experiences.append(entry)
        # 最多保留 100 条
        if len(self.experiences) > 100:
            self.experiences = self.experiences[-100:]
        self._save()

    def search(self, keyword: str, top_k: int = 3) -> list[dict]:
        """关键词搜索相关经验"""
        results = []
        kw = keyword.lower()
        for exp in self.experiences:
            if kw in exp["task"].lower() or kw in exp["lesson"].lower():
                results.append(exp)
        return results[-top_k:]

    def get_for_context(self) -> str:
        """获取最近经验作为上下文"""
        recent = self.experiences[-5:]
        if not recent:
            return ""
        return "相关经验:\n" + "\n".join(
            f"- {e['task']}: {e['lesson']}" for e in recent
        )
