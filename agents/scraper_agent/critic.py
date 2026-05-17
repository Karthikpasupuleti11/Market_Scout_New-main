import json
from typing import List, Dict

from llm.nvidia_client import invoke_llm


BATCH_SIZE = 5


async def batch_is_technical(
    articles: List[Dict]
) -> List[bool]:

    if not articles:
        return []

    article_blocks = []

    for idx, article in enumerate(articles):

        title = article.get("title", "")

        text = (
            article.get("text", "")
            or article.get("article_text", "")
        )

        trimmed_text = text[:800]

        article_blocks.append(
            f"""
ID: {idx}

TITLE:
{title}

TEXT:
{trimmed_text}
"""
        )

    joined_articles = "\n\n".join(article_blocks)

    prompt = f"""
Determine whether each article below contains REAL technical updates.

Technical updates include:
- APIs
- SDKs
- AI models
- infra/platform releases
- developer tools
- engineering announcements
- technical product launches

Reject:
- marketing
- stock news
- opinions
- general news
- vague announcements

Respond ONLY in valid JSON.

Example:
[
    {{"id": 0, "technical": true}},
    {{"id": 1, "technical": false}}
]

ARTICLES:
{joined_articles}
"""

    raw_response = await invoke_llm(
        [{"role": "user", "content": prompt}],
        temperature=0.0,
        max_tokens=300,
    )

    try:

        if isinstance(raw_response, str):
            parsed = json.loads(raw_response)

        elif isinstance(raw_response, list):
            parsed = raw_response

        else:
            return [False] * len(articles)

    except Exception:
        return [False] * len(articles)

    results = [False] * len(articles)

    for item in parsed:

        try:
            idx = item["id"]

            technical = item["technical"]

            if 0 <= idx < len(results):
                results[idx] = technical

        except Exception:
            continue

    return results