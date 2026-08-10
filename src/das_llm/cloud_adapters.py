import os
import json
import urllib.request
import asyncio
from typing import List, Dict, Any, Optional
from das_llm.adapter import AgentAdapter
from das_llm.schemas import Message


class OpenAIAgentAdapter(AgentAdapter):
    """Adapter driving an agent powered by OpenAI models (e.g., gpt-4o)."""

    def __init__(
        self,
        model: str = "gpt-4o",
        api_key: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ):
        self.model = model
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.system_prompt = system_prompt or "You are a helpful assistant with tool access."

    async def invoke(
        self, prompt: str, das_mock_tools: Optional[Dict[str, Any]] = None
    ) -> List[Message]:
        if not self.api_key:
            # Fallback for testing environments without live API keys
            return self._mock_fallback(prompt, das_mock_tools)

        # Real OpenAI API call using standard urllib endpoint
        url = "https://api.openai.com/v1/chat/completions"
        payload = json.dumps(
            {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt},
                ],
            }
        ).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
        )

        def _do_request():
            with urllib.request.urlopen(req) as resp:
                return json.loads(resp.read().decode("utf-8"))

        res = await asyncio.to_thread(_do_request)
        content = res["choices"][0]["message"].get("content", "")
        return [
            Message(role="system", content=self.system_prompt),
            Message(role="user", content=prompt),
            Message(role="assistant", content=content),
        ]

    def _mock_fallback(self, prompt: str, das_mock_tools=None) -> List[Message]:
        return [
            Message(role="system", content=self.system_prompt),
            Message(role="user", content=prompt),
            Message(role="assistant", content="OpenAI mock response (no API key supplied)."),
        ]


class ClaudeAgentAdapter(AgentAdapter):
    """Adapter driving an agent powered by Anthropic Claude models (e.g., claude-3-5-sonnet)."""

    def __init__(
        self,
        model: str = "claude-3-5-sonnet-20241022",
        api_key: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ):
        self.model = model
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
        self.system_prompt = system_prompt or "You are a helpful assistant with tool access."

    async def invoke(
        self, prompt: str, das_mock_tools: Optional[Dict[str, Any]] = None
    ) -> List[Message]:
        if not self.api_key:
            return [
                Message(role="system", content=self.system_prompt),
                Message(role="user", content=prompt),
                Message(role="assistant", content="Claude mock response (no API key supplied)."),
            ]

        url = "https://api.anthropic.com/v1/messages"
        payload = json.dumps(
            {
                "model": self.model,
                "max_tokens": 1024,
                "system": self.system_prompt,
                "messages": [{"role": "user", "content": prompt}],
            }
        ).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
            },
        )

        def _do_request():
            with urllib.request.urlopen(req) as resp:
                return json.loads(resp.read().decode("utf-8"))

        res = await asyncio.to_thread(_do_request)
        content = res["content"][0]["text"]
        return [
            Message(role="system", content=self.system_prompt),
            Message(role="user", content=prompt),
            Message(role="assistant", content=content),
        ]
