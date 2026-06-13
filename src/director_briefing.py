"""Strategic Director Briefing using the 5-hat consulting framework.

Applies the Global Consulting Director persona (Sales, Strategist, Architect,
Product, Project) to each news item. Output is ≤150 words total across 6
structured bullets.
"""

from __future__ import annotations

from src.llm_client import LLMClient
from src.types import Article

_DIRECTOR_SYSTEM_PROMPT = """\
You are a Global Consulting Director covering enterprise tech news \
(AI, Fintech, Web3, Cyber). Apply the 5 Operating Hats to each \
news item individually.

Output per news item (≤150 words total - HARD limit across all 6 \
bullets combined):

- **Executive Synthesis:** [1 punchy bullet - macroeconomic or \
industry impact]
- **Corporate Strategy (Strategist):** [1 bullet - market positioning \
shift, business model evolution, ecosystem play]
- **Commercial Angle (Sales):** [1 bullet - client pain points, \
pitch strategy, ROI vector]
- **Architectural & Security Blueprint (Tech):** [1 bullet - \
integration feasibility, cyber threat vectors, compliance risks]
- **Product & Experience Vision (Product):** [1 bullet - highest-value \
enterprise MVP, competitive moat]
- **Delivery Reality (Project):** [1 bullet - time-to-value, \
implementation complexity, next steps]

Strictly bullet points under these headers - no paragraph prose, no \
intro/outro text.
Maximum 150 words across all 6 bullets combined (ultra-dense, ~20-25 \
words each).
Professional executive tone. Direct, confident statements. No hedging \
("might", "could", "perhaps")."""


def generate_briefing(
    article: Article, llm: LLMClient
) -> str:
    """Generate a Strategic Director Briefing for a single article.

    Args:
        article: Article with full_text (or summary) populated.
        llm: Configured LLM client.

    Returns:
        Formatted Director Briefing string, or fallback text on error.
    """
    content = article.full_text or article.summary
    if not content:
        return (
            "### 📊 STRATEGIC DIRECTOR BRIEFING\n"
            "- No content available for analysis."
        )

    user_prompt = (
        f"Analyze this Article through the Director's 5-Hat Framework:\n\n"
        f"Title: {article.title}\n\n"
        f"Content:\n{content[:6000]}"
    )

    try:
        briefing = llm.chat(
            system_prompt=_DIRECTOR_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.3,
            max_tokens=800,
        )
        return briefing
    except RuntimeError:
        return (
            "### 📊 STRATEGIC DIRECTOR BRIEFING\n"
            "- Briefing generation failed due to API error."
        )
