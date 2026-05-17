"""
Market Intelligence Scout — LLM Client (NVIDIA NIM)

Multi-key pool with per-key token-bucket rate limit, prompt-level cache
for deterministic (temperature=0) calls, retry with exponential back-off.

Exposes both sync (`invoke_llm`, `invoke_llm_with_tools`) and async
(`ainvoke_llm`, `ainvoke_llm_with_tools`) variants. Async path uses
`AsyncOpenAI` + per-key `asyncio.Semaphore` for concurrency capping and
an async token bucket for RPM rate limiting.
"""

import asyncio
import hashlib
import json
import logging
import threading
import time
from collections import deque
from itertools import cycle
from typing import List, Dict, Optional

from openai import OpenAI, AsyncOpenAI

from app.config import settings
from cache.redis_client import make_cache_key, get_cache, set_cache
from observability.metrics import LLM_CALL_COUNT, LLM_LATENCY, LLM_TOKEN_USAGE

logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────────────────
# Token Bucket — per key, sliding 60s window (SYNC)
# ────────────────────────────────────────────────────────────────────

class TokenBucket:
    def __init__(self, rpm: int):
        self.rpm = rpm
        self.window = 60.0
        self.calls: deque = deque()
        self.cond = threading.Condition(threading.Lock())

    def acquire(self) -> None:
        with self.cond:
            while True:
                now = time.monotonic()
                while self.calls and now - self.calls[0] > self.window:
                    self.calls.popleft()
                if len(self.calls) < self.rpm:
                    self.calls.append(now)
                    return
                wait = self.window - (now - self.calls[0]) + 0.01
                self.cond.wait(timeout=max(0.05, wait))


# ────────────────────────────────────────────────────────────────────
# Async Token Bucket — per key, sliding 60s window
# ────────────────────────────────────────────────────────────────────

class AsyncTokenBucket:
    def __init__(self, rpm: int):
        self.rpm = rpm
        self.window = 60.0
        self.calls: deque = deque()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        while True:
            async with self._lock:
                now = time.monotonic()
                while self.calls and now - self.calls[0] > self.window:
                    self.calls.popleft()
                if len(self.calls) < self.rpm:
                    self.calls.append(now)
                    return
                wait = self.window - (now - self.calls[0]) + 0.01
            await asyncio.sleep(max(0.05, wait))


# ────────────────────────────────────────────────────────────────────
# Key Pool
# ────────────────────────────────────────────────────────────────────

def _load_keys() -> List[str]:
    raw = settings.NVIDIA_API_KEYS or settings.NVIDIA_API_KEY
    keys = [k.strip() for k in raw.split(",") if k.strip()]
    if not keys:
        raise RuntimeError("No NVIDIA API keys configured.")
    return keys


_keys = _load_keys()

# Sync state
_clients: Dict[str, OpenAI] = {}
_buckets: Dict[str, TokenBucket] = {k: TokenBucket(settings.LLM_RPM_PER_KEY) for k in _keys}
_cycle_lock = threading.Lock()
_cycle = cycle(_keys)

# Async state — primitives created lazily on first use (bound to running loop)
_async_clients: Dict[str, AsyncOpenAI] = {}
_async_buckets: Dict[str, AsyncTokenBucket] = {}
_async_semaphores: Dict[str, asyncio.Semaphore] = {}
_async_init_lock = threading.Lock()
_async_cycle_lock = asyncio.Lock()
_async_cycle = cycle(_keys)

logger.info("LLM — key pool size=%d rpm_per_key=%d total_rpm=%d concurrency_per_key=%d",
            len(_keys), settings.LLM_RPM_PER_KEY,
            len(_keys) * settings.LLM_RPM_PER_KEY,
            settings.LLM_CONCURRENCY_PER_KEY)


def _next_key() -> str:
    with _cycle_lock:
        return next(_cycle)


def _client_for(key: str) -> OpenAI:
    c = _clients.get(key)
    if c is None:
        c = OpenAI(base_url="https://integrate.api.nvidia.com/v1", api_key=key)
        _clients[key] = c
    return c


# ── Async primitive accessors ───────────────────────────────────────

async def _anext_key() -> str:
    async with _async_cycle_lock:
        return next(_async_cycle)


def _aclient_for(key: str) -> AsyncOpenAI:
    c = _async_clients.get(key)
    if c is None:
        with _async_init_lock:
            c = _async_clients.get(key)
            if c is None:
                c = AsyncOpenAI(
                    base_url="https://integrate.api.nvidia.com/v1",
                    api_key=key,
                )
                _async_clients[key] = c
    return c


def _abucket_for(key: str) -> AsyncTokenBucket:
    b = _async_buckets.get(key)
    if b is None:
        with _async_init_lock:
            b = _async_buckets.get(key)
            if b is None:
                b = AsyncTokenBucket(settings.LLM_RPM_PER_KEY)
                _async_buckets[key] = b
    return b


def _asem_for(key: str) -> asyncio.Semaphore:
    s = _async_semaphores.get(key)
    if s is None:
        with _async_init_lock:
            s = _async_semaphores.get(key)
            if s is None:
                s = asyncio.Semaphore(settings.LLM_CONCURRENCY_PER_KEY)
                _async_semaphores[key] = s
    return s


# ────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────

def _infer_agent_name(messages: List[Dict[str, str]]) -> str:
    if not messages:
        return "unknown"

    system_msg = (
        messages[0]
        .get("content", "")
        .lower()
    )

    if "security" in system_msg:
        return "guardrails"

    if "search" in system_msg:
        return "search_planner"

    if "content classifier" in system_msg:
        return "content_filter"

    if "credibility" in system_msg:
        return "authority_check"

    if "extraction" in system_msg:
        return "feature_extraction"

    if "intelligence analyst" in system_msg:
        return "synthesis"

    return "unknown"


def _prompt_cache_key(messages, temperature, max_tokens) -> str:
    payload = json.dumps({
        "m": messages,
        "t": temperature,
        "k": max_tokens,
        "model": settings.LLM_MODEL,
    }, sort_keys=True, default=str)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]
    return make_cache_key("llm", digest)


# ────────────────────────────────────────────────────────────────────
# Core LLM Invocation (SYNC)
# ────────────────────────────────────────────────────────────────────

def invoke_llm(
    messages: List[Dict[str, str]],
    temperature: float = settings.LLM_TEMPERATURE,
    max_tokens: int = settings.LLM_MAX_TOKENS,
    retries: int = settings.MAX_RETRIES,
) -> str:
    agent_name = _infer_agent_name(messages)

    cache_key: Optional[str] = None
    if temperature == 0:
        cache_key = _prompt_cache_key(messages, temperature, max_tokens)
        cached = get_cache(cache_key)
        if cached is not None:
            LLM_CALL_COUNT.labels(agent_name=agent_name, status="cache_hit").inc()
            logger.debug("LLM CACHE HIT agent=%s", agent_name)
            return cached

    last_error: Optional[Exception] = None

    for attempt in range(1, retries + 1):
        key = _next_key()
        _buckets[key].acquire()
        client = _client_for(key)

        start_time = time.time()

        try:
            response = client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=settings.LLM_TOP_P,
            )

            duration = time.time() - start_time

            content = response.choices[0].message.content

            LLM_CALL_COUNT.labels(agent_name=agent_name, status="success").inc()
            LLM_LATENCY.labels(agent_name=agent_name).observe(duration)
            if response.usage:
                LLM_TOKEN_USAGE.labels(
                    agent_name=agent_name, token_type="prompt"
                ).inc(response.usage.prompt_tokens)
                LLM_TOKEN_USAGE.labels(
                    agent_name=agent_name, token_type="completion"
                ).inc(response.usage.completion_tokens)

            if cache_key and content:
                set_cache(cache_key, content, expire=settings.LLM_PROMPT_CACHE_TTL)

            logger.debug(
                "LLM OK key=...%s tokens=%s attempt=%d duration=%.2fs",
                key[-6:],
                response.usage.total_tokens if response.usage else "?",
                attempt,
                duration,
            )

            return content

        except Exception as exc:
            duration = time.time() - start_time
            last_error = exc
            LLM_CALL_COUNT.labels(agent_name=agent_name, status="retry").inc()
            LLM_LATENCY.labels(agent_name=agent_name).observe(duration)

            wait = 2 ** attempt
            logger.warning(
                "LLM FAIL attempt=%d/%d key=...%s error=%s — retrying in %ds",
                attempt, retries, key[-6:], exc, wait,
            )

            if attempt < retries:
                time.sleep(wait)

    LLM_CALL_COUNT.labels(agent_name=agent_name, status="failure").inc()
    raise RuntimeError(
        f"LLM invocation failed after {retries} retries: {last_error}"
    )


# ────────────────────────────────────────────────────────────────────
# Core LLM Invocation (ASYNC)
# ────────────────────────────────────────────────────────────────────

async def ainvoke_llm(
    messages: List[Dict[str, str]],
    temperature: float = settings.LLM_TEMPERATURE,
    max_tokens: int = settings.LLM_MAX_TOKENS,
    retries: int = settings.MAX_RETRIES,
) -> str:
    agent_name = _infer_agent_name(messages)

    cache_key: Optional[str] = None
    if temperature == 0:
        cache_key = _prompt_cache_key(messages, temperature, max_tokens)
        cached = await asyncio.to_thread(get_cache, cache_key)
        if cached is not None:
            LLM_CALL_COUNT.labels(agent_name=agent_name, status="cache_hit").inc()
            logger.debug("LLM CACHE HIT agent=%s", agent_name)
            return cached

    last_error: Optional[Exception] = None

    for attempt in range(1, retries + 1):
        key = await _anext_key()
        sem = _asem_for(key)
        bucket = _abucket_for(key)
        client = _aclient_for(key)

        async with sem:
            await bucket.acquire()
            start_time = time.time()

            try:
                response = await client.chat.completions.create(
                    model=settings.LLM_MODEL,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    top_p=settings.LLM_TOP_P,
                )

                duration = time.time() - start_time

                content = response.choices[0].message.content

                LLM_CALL_COUNT.labels(agent_name=agent_name, status="success").inc()
                LLM_LATENCY.labels(agent_name=agent_name).observe(duration)
                if response.usage:
                    LLM_TOKEN_USAGE.labels(
                        agent_name=agent_name, token_type="prompt"
                    ).inc(response.usage.prompt_tokens)
                    LLM_TOKEN_USAGE.labels(
                        agent_name=agent_name, token_type="completion"
                    ).inc(response.usage.completion_tokens)

                if cache_key and content:
                    await asyncio.to_thread(
                        set_cache, cache_key, content,
                        settings.LLM_PROMPT_CACHE_TTL,
                    )

                logger.debug(
                    "LLM OK key=...%s tokens=%s attempt=%d duration=%.2fs",
                    key[-6:],
                    response.usage.total_tokens if response.usage else "?",
                    attempt,
                    duration,
                )

                return content

            except Exception as exc:
                duration = time.time() - start_time
                last_error = exc
                LLM_CALL_COUNT.labels(agent_name=agent_name, status="retry").inc()
                LLM_LATENCY.labels(agent_name=agent_name).observe(duration)

                wait = 2 ** attempt
                logger.warning(
                    "LLM FAIL attempt=%d/%d key=...%s error=%s — retrying in %ds",
                    attempt, retries, key[-6:], exc, wait,
                )

        if attempt < retries:
            await asyncio.sleep(wait)

    LLM_CALL_COUNT.labels(agent_name=agent_name, status="failure").inc()
    raise RuntimeError(
        f"LLM invocation failed after {retries} retries: {last_error}"
    )


# ────────────────────────────────────────────────────────────────────
# Tool-Calling LLM Invocation (SYNC)
# ────────────────────────────────────────────────────────────────────

def invoke_llm_with_tools(
    messages: List[Dict[str, str]],
    tools: List[Dict],
    temperature: float = settings.LLM_TEMPERATURE,
    max_tokens: int = settings.LLM_MAX_TOKENS,
):
    """
    Tool-calling variant. Same key pool + bucket, no prompt cache (tool calls
    are typically non-deterministic).
    """
    key = _next_key()
    _buckets[key].acquire()
    client = _client_for(key)

    return client.chat.completions.create(
        model=settings.LLM_MODEL,
        messages=messages,
        tools=tools,
        tool_choice="auto",
        temperature=temperature,
        max_tokens=max_tokens,
        top_p=settings.LLM_TOP_P,
    )


# ────────────────────────────────────────────────────────────────────
# Tool-Calling LLM Invocation (ASYNC)
# ────────────────────────────────────────────────────────────────────

async def ainvoke_llm_with_tools(
    messages: List[Dict[str, str]],
    tools: List[Dict],
    temperature: float = settings.LLM_TEMPERATURE,
    max_tokens: int = settings.LLM_MAX_TOKENS,
):
    key = await _anext_key()
    sem = _asem_for(key)
    bucket = _abucket_for(key)
    client = _aclient_for(key)

    async with sem:
        await bucket.acquire()
        return await client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=messages,
            tools=tools,
            tool_choice="auto",
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=settings.LLM_TOP_P,
        )
