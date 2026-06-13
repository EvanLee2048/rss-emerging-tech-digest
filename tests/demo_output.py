#!/usr/bin/env python3
"""Demo: show the exact digest output format the pipeline produces, with dates."""

from src.digest_assembler import assemble_digest
from src.types import Article

articles = [
    Article(
        title="AI Infrastructure Startup Raises $500M Series C at $5B Valuation",
        url="https://example.com/ai-funding",
        summary="",
        guid="g1",
        feed_key="semianalysis",
        feed_label="SemiAnalysis",
        category="AI & Digital Transformation",
        url_hash="abc123",
        date="2024-06-12",
        full_text="Full article text...",
        is_hkma=False,
        filter_passed=True,
        bullets=(
            "- Startup raised $500M in Series C funding at $5B valuation\n"
            "- Investment led by Sequoia Capital and Andreessen Horowitz\n"
            "- Funds earmarked for AI training infrastructure expansion\n"
            "- Company projects 3x revenue growth to $200M in FY2026\n"
            "- New data centers planned across US, EU, and APAC regions\n"
            "- Competes with CoreWeave and Lambda Labs in GPU cloud market"
        ),
        director_briefing=(
            "- **Executive Synthesis:** AI infra capex surge signals\n"
            "  hyperscaler demand outpacing supply through 2027\n"
            "- **Corporate Strategy (Strategist):** Vertical integration\n"
            "  play locks enterprise AI dependency away from Big Tech\n"
            "- **Commercial Angle (Sales):** $200B+ TAM for AI\n"
            "  inference infrastructure; price anchoring vs hyperscalers\n"
            "- **Architectural & Security Blueprint (Tech):** Multi-region\n"
            "  GPU cluster design requires zero-trust and data residency\n"
            "- **Product & Experience Vision (Product):** Self-service\n"
            "  API portal reduces enterprise onboarding weeks to hours\n"
            "- **Delivery Reality (Project):** 18-month build cycle;\n"
            "  grid interconnection permits are critical path risk"
        ),
    ),
    Article(
        title="HKMA Issues New Guidelines for AI Governance in Banking",
        url="https://example.com/hkma-ai",
        summary="",
        guid="g2",
        feed_key="hkma",
        feed_label="HKMA Press Releases",
        category="HK Tech Regulation",
        url_hash="def456",
        date="2024-06-13",
        full_text="Full article text...",
        is_hkma=True,
        filter_passed=True,
        filter_reason="AI governance guideline - keep",
        bullets=(
            "- HKMA published new AI governance framework for authorized\n"
            "  institutions\n"
            "- Requirements include model explainability and bias testing\n"
            "- Banks must appoint a designated AI risk officer by Q1 2027\n"
            "- Non-compliance penalties up to HKD 10M per violation"
        ),
        director_briefing=(
            "- **Executive Synthesis:** HK joins US/EU/SG in AI\n"
            "  regulatory alignment; first-mover compliance cost vs\n"
            "  market access trade-off\n"
            "- **Corporate Strategy (Strategist):** First-mover advantage\n"
            "  for banks that operationalize AI governance as differentiator\n"
            "- **Commercial Angle (Sales):** Consultancy pipeline: AI\n"
            "  audit + remediation services at HKD 2-5M per institution\n"
            "- **Architectural & Security Blueprint (Tech):** Model\n"
            "  registry + explainability layer; legacy ML pipelines retool\n"
            "- **Product & Experience Vision (Product):** Compliance\n"
            "  dashboard as SaaS; white-label for regional banks\n"
            "- **Delivery Reality (Project):** 9-12 month implementation;\n"
            "  talent shortage for AI risk officers is binding constraint"
        ),
    ),
]

digest = assemble_digest(
    articles,
    feeds_scanned=10,
    categories_with_new=["AI & Digital Transformation", "HK Tech Regulation"],
)
print(digest)
