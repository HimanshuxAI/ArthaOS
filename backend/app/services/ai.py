import httpx

from app.core.config import get_settings


async def enhance_answer_with_llm(question: str, deterministic_answer: str, report: dict) -> str:
    settings = get_settings()
    if not settings.openai_api_key:
        return deterministic_answer

    prompt = (
        "You are ArthaOS, an AI CFO for Indian freelancers and small businesses. "
        "Use only the provided financial facts. Keep the answer concise and practical.\n\n"
        f"Question: {question}\n"
        f"Deterministic answer: {deterministic_answer}\n"
        f"Report facts: {report}\n"
    )
    try:
        async with httpx.AsyncClient(timeout=12) as client:
            response = await client.post(
                f"{settings.openai_base_url.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                json={
                    "model": settings.openai_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.2,
                },
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            return content.strip() or deterministic_answer
    except Exception:
        return deterministic_answer
