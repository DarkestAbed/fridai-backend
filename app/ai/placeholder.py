# GPL-3.0-only
from dataclasses import dataclass

@dataclass
class LangChainPlaceholder:
    """Minimal stub demonstrating where LangChain logic could live.
    Hook up your provider and chains here in the future.
    """
    def summarize(self, text: str) -> str:
        return text[:200] + ("..." if len(text) > 200 else "")
