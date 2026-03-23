"""
Citability Score — Content analysis with the 9 Princeton GEO methods (KDD 2024).

Each detect_*() function analyzes one aspect of HTML content and returns
a MethodScore. No ML dependencies — only regex, HTML tags and structural metrics.

Paper: "GEO: Generative Engine Optimization" (arxiv.org/abs/2311.09735)
"""

from __future__ import annotations

import re
from collections import Counter
from urllib.parse import urlparse

from geo_optimizer.models.results import CitabilityResult, MethodScore

# ─── Constants ────────────────────────────────────────────────────────────────

# Authoritative domains for Cite Sources
_AUTHORITATIVE_TLDS = {".edu", ".gov", ".org"}
_AUTHORITATIVE_DOMAINS = {
    "wikipedia.org",
    "pubmed.ncbi.nlm.nih.gov",
    "scholar.google.com",
    "nature.com",
    "sciencedirect.com",
    "jstor.org",
    "arxiv.org",
    "ncbi.nlm.nih.gov",
    "who.int",
    "cdc.gov",
    "europa.eu",
    "springer.com",
    "ieee.org",
}

# Attribution quote pattern: "text" — Author
_QUOTE_ATTRIBUTION_RE = re.compile(
    r'["\u201c].{10,300}["\u201d]\s*(?:[-\u2014\u2013]|—|–)\s*\w+',
    re.DOTALL,
)

# Statistics patterns
_STAT_PATTERNS = [
    r"\b\d+(?:\.\d+)?%",
    r"\b\d{1,3}(?:,\d{3})+(?:\.\d+)?\b",
    r"\$\d+(?:[.,]\d+)*(?:\s*(?:M|B|K|million|billion|thousand))?\b",
    r"\b\d+\s*(?:million|billion|trillion|thousand)\b",
    r"\b\d+(?:\.\d+)?\s*(?:x|X)\b",
]
_STAT_RE = re.compile("|".join(_STAT_PATTERNS), re.IGNORECASE)

# Logical connectives (EN + IT)
_CONNECTIVES = re.compile(
    r"\b(?:therefore|consequently|furthermore|moreover|however|nevertheless"
    r"|in addition|as a result|for example|for instance|in conclusion"
    r"|specifically|in particular|in contrast"
    r"|quindi|pertanto|di conseguenza|inoltre|innanzitutto|infatti"
    r"|tuttavia|nonostante|in particolare|ad esempio|come risultato)\b",
    re.IGNORECASE,
)

# Authoritative tone markers
_AUTHORITY_RE = re.compile(
    r"\b(?:according to|research (?:shows?|indicates?|demonstrates?)"
    r"|studies? (?:show|indicate|demonstrate|confirm)"
    r"|evidence (?:shows?|suggests?|indicates?)"
    r"|experts? (?:agree|recommend|suggest)"
    r"|data (?:shows?|indicates?|reveals?)"
    r"|proven|demonstrated|established)\b",
    re.IGNORECASE,
)

# Excessive hedging
_HEDGE_RE = re.compile(
    r"\b(?:might be|could possibly|maybe|perhaps|somewhat|kind of|sort of|seems like)\b",
    re.IGNORECASE,
)

# Technical terminology patterns
_TECH_PATTERNS = [
    r"\b[A-Z]{2,6}\b",
    r"\bv\d+\.\d+(?:\.\d+)?\b",
    r"\bRFC\s*\d+\b",
    r"\bISO\s*\d+\b",
    r"\b(?:IEEE|IETF|W3C|ECMA)\b",
    r"`[^`]+`",
]
_TECH_RE = re.compile("|".join(_TECH_PATTERNS))

# Stop words for TTR (basic English)
_STOP_WORDS = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "but",
    "in",
    "on",
    "at",
    "to",
    "for",
    "of",
    "with",
    "by",
    "from",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "have",
    "has",
    "had",
    "do",
    "does",
    "did",
    "will",
    "would",
    "could",
    "should",
    "may",
    "might",
    "shall",
    "this",
    "that",
    "these",
    "those",
    "it",
    "its",
    "not",
    "no",
    "can",
    "so",
    "if",
    "then",
    "than",
    "also",
}


# ─── Helper function ─────────────────────────────────────────────────────────


def _get_clean_text(soup) -> str:
    """Extract clean text by removing script, style, nav, footer."""
    from bs4 import BeautifulSoup

    clean = BeautifulSoup(str(soup), "html.parser")
    for tag in clean(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    return clean.get_text(separator=" ", strip=True)


# ─── 1. Cite Sources (+27%) ──────────────────────────────────────────────────


def detect_cite_sources(soup, base_url: str) -> MethodScore:
    """Detect citations to authoritative sources (.edu, .gov, Wikipedia, etc.)."""
    parsed_base = urlparse(base_url)
    base_domain = parsed_base.netloc.replace("www.", "")

    authoritative_count = 0
    external_count = 0

    for a in soup.find_all("a", href=True):
        href = a["href"]
        if not href.startswith("http"):
            continue
        link_domain = urlparse(href).netloc.replace("www.", "")
        if link_domain == base_domain:
            continue
        external_count += 1
        tld = "." + link_domain.split(".")[-1] if "." in link_domain else ""
        if tld in _AUTHORITATIVE_TLDS or any(d in link_domain for d in _AUTHORITATIVE_DOMAINS):
            authoritative_count += 1

    # References/bibliography section
    ref_headings = [
        h
        for h in soup.find_all(["h2", "h3", "h4"])
        if re.search(r"references?|sources?|bibliograph|citazion", h.get_text(), re.I)
    ]
    cite_tags = len(soup.find_all("cite"))

    score = min(authoritative_count * 3 + external_count + cite_tags * 2 + len(ref_headings) * 3, 12)
    detected = authoritative_count >= 2 or bool(ref_headings) or cite_tags >= 1

    return MethodScore(
        name="cite_sources",
        label="Cite Sources",
        detected=detected,
        score=score,
        max_score=12,
        impact="+27%",
        details={
            "authoritative_links": authoritative_count,
            "external_links": external_count,
            "cite_tags": cite_tags,
            "has_reference_section": bool(ref_headings),
        },
    )


# ─── 2. Quotation Addition (+41%) ────────────────────────────────────────────


def detect_quotations(soup) -> MethodScore:
    """Detect attributed quotes (blockquote, attributed quoted text)."""
    blockquotes = soup.find_all("blockquote")
    q_tags = soup.find_all("q")

    # Blockquote with cite attribute = formal citation
    bq_with_cite = [bq for bq in blockquotes if bq.get("cite") or bq.find("cite")]

    # Text pattern "..." — Author
    body_text = soup.get_text(separator=" ")
    text_attributions = _QUOTE_ATTRIBUTION_RE.findall(body_text)

    # Pull quotes (CSS class)
    pull_quotes = soup.find_all(
        ["figure", "aside", "div"],
        class_=re.compile(r"pull.?quote|blockquote|testimonial", re.I),
    )

    total = len(blockquotes) + len(q_tags) + len(text_attributions) + len(pull_quotes)
    score = min(total * 3 + len(bq_with_cite) * 2, 15)

    return MethodScore(
        name="quotation_addition",
        label="Quotation Addition",
        detected=total >= 1,
        score=score,
        max_score=15,
        impact="+41%",
        details={
            "blockquotes": len(blockquotes),
            "q_tags": len(q_tags),
            "attributed_quotes": len(text_attributions),
            "pull_quotes": len(pull_quotes),
        },
    )


# ─── 3. Statistics Addition (+33%) ───────────────────────────────────────────


def detect_statistics(soup, clean_text: str | None = None) -> MethodScore:
    """Detect statistical and quantitative data in content."""
    body_text = clean_text or _get_clean_text(soup)
    matches = _STAT_RE.findall(body_text)

    # Tables with numerical data (separator=" " to avoid concatenation without spaces)
    tables_with_data = sum(1 for t in soup.find_all("table") if _STAT_RE.search(t.get_text(separator=" ")))

    # HTML5 data elements
    data_elements = len(soup.find_all(["data", "meter", "progress"]))

    word_count = max(len(body_text.split()), 1)
    density = len(matches) / word_count * 1000

    score = min(int(density * 2) + tables_with_data * 3 + data_elements * 2, 13)

    return MethodScore(
        name="statistics_addition",
        label="Statistics Addition",
        detected=len(matches) >= 3,
        score=score,
        max_score=13,
        impact="+33%",
        details={
            "stat_matches": len(matches),
            "density_per_1000_words": round(density, 2),
            "tables_with_data": tables_with_data,
        },
    )


# ─── 4. Fluency Optimization (+29%) ──────────────────────────────────────────


def detect_fluency(soup) -> MethodScore:
    """Estimate text fluency through structural heuristics."""
    paragraphs = soup.find_all("p")
    if not paragraphs:
        return MethodScore(name="fluency_optimization", label="Fluency Optimization", max_score=12, impact="+29%")

    # Average paragraph length
    para_lengths = [len(p.get_text().split()) for p in paragraphs if p.get_text().strip()]
    avg_para_len = sum(para_lengths) / max(len(para_lengths), 1)

    # Logical connectives
    body_text = soup.get_text(separator=" ")
    connective_count = len(_CONNECTIVES.findall(body_text))

    # Text-to-list ratio
    list_items = soup.find_all("li")
    text_to_list_ratio = len(paragraphs) / max(len(list_items), 1)

    score = 0
    if avg_para_len >= 30:
        score += 4
    elif avg_para_len >= 15:
        score += 2
    score += min(connective_count // 2, 4)
    if text_to_list_ratio >= 1.5:
        score += 2
    if len(paragraphs) >= 5:
        score += 2

    return MethodScore(
        name="fluency_optimization",
        label="Fluency Optimization",
        detected=score >= 4,
        score=min(score, 12),
        max_score=12,
        impact="+29%",
        details={
            "avg_paragraph_words": round(avg_para_len, 1),
            "connective_count": connective_count,
            "paragraphs": len(paragraphs),
            "list_items": len(list_items),
        },
    )


# ─── 5. Technical Terms (+18%) ───────────────────────────────────────────────


def detect_technical_terms(soup, clean_text: str | None = None) -> MethodScore:
    """Detect density of technical terminology in content."""
    body_text = clean_text or _get_clean_text(soup)
    tech_matches = _TECH_RE.findall(body_text)

    code_blocks = len(soup.find_all(["code", "pre", "kbd", "samp"]))
    abbr_tags = len(soup.find_all("abbr"))
    dfn_tags = len(soup.find_all("dfn"))

    word_count = max(len(body_text.split()), 1)
    density = len(tech_matches) / word_count * 1000

    score = min(int(density) + code_blocks * 2 + abbr_tags + dfn_tags, 10)

    return MethodScore(
        name="technical_terms",
        label="Technical Terms",
        detected=density >= 5 or code_blocks >= 1,
        score=score,
        max_score=10,
        impact="+18%",
        details={
            "tech_matches": len(tech_matches),
            "density_per_1000": round(density, 2),
            "code_blocks": code_blocks,
            "abbr_tags": abbr_tags,
        },
    )


# ─── 6. Authoritative Tone (+16%) ────────────────────────────────────────────


def detect_authoritative_tone(soup) -> MethodScore:
    """Detect authoritative tone signals and author credentials."""
    body_text = soup.get_text(separator=" ")

    authority_signals = len(_AUTHORITY_RE.findall(body_text))
    hedge_signals = len(_HEDGE_RE.findall(body_text))

    # Author bio
    author_bio = soup.find_all(
        ["div", "section", "aside"],
        class_=re.compile(r"author|bio|about-author|byline|contributor", re.I),
    )
    author_schema = soup.find_all("span", attrs={"itemprop": "author"})

    # Credentials
    credentials = re.findall(r"\b(?:Dr\.?|Prof\.?|PhD|M\.?D\.?|MBA|MSc|BSc|CEO|CTO)\b", body_text)

    # Author meta tag
    author_meta = soup.find("meta", attrs={"name": re.compile(r"author", re.I)})

    score = 0
    score += min(authority_signals, 4)
    score -= min(hedge_signals // 3, 2)
    score += min(len(author_bio) + len(author_schema), 3)
    score += min(len(credentials), 2)
    score += 1 if author_meta else 0

    return MethodScore(
        name="authoritative_tone",
        label="Authoritative Tone",
        detected=max(score, 0) >= 3,
        score=max(min(score, 10), 0),
        max_score=10,
        impact="+16%",
        details={
            "authority_markers": authority_signals,
            "hedge_markers": hedge_signals,
            "has_author_bio": bool(author_bio or author_schema),
            "credentials": list(set(credentials))[:5],
            "has_author_meta": bool(author_meta),
        },
    )


# ─── 7. Easy-to-Understand (+14%) ────────────────────────────────────────────


def detect_easy_to_understand(soup) -> MethodScore:
    """Estimate readability with structural metrics."""
    main = soup.find("main") or soup.find("article") or soup
    paragraphs = main.find_all("p") if main else []

    all_sentences = []
    for p in paragraphs:
        text = p.get_text(separator=" ")
        for s in re.split(r"[.!?]+", text):
            words = s.split()
            if len(words) >= 3:
                all_sentences.append(words)

    if not all_sentences:
        return MethodScore(name="easy_to_understand", label="Easy-to-Understand", max_score=8, impact="+14%")

    avg_sentence_len = sum(len(s) for s in all_sentences) / len(all_sentences)

    # Heading hierarchy
    h2_count = len(soup.find_all("h2"))
    h3_count = len(soup.find_all("h3"))

    # FAQ sections
    faq_headings = [
        h for h in soup.find_all(["h2", "h3"]) if re.search(r"faq|domand|question|how to|come", h.get_text(), re.I)
    ]

    score = 0
    if avg_sentence_len <= 15:
        score += 3
    elif avg_sentence_len <= 20:
        score += 2
    if h2_count >= 3:
        score += 2
    elif h2_count >= 1:
        score += 1
    if h3_count >= 1:
        score += 1
    score += min(len(faq_headings), 2)

    return MethodScore(
        name="easy_to_understand",
        label="Easy-to-Understand",
        detected=score >= 3,
        score=min(score, 8),
        max_score=8,
        impact="+14%",
        details={
            "avg_sentence_length": round(avg_sentence_len, 1),
            "h2_count": h2_count,
            "h3_count": h3_count,
            "faq_sections": len(faq_headings),
        },
    )


# ─── 8. Unique Words (+7%) ───────────────────────────────────────────────────


def detect_unique_words(soup, clean_text: str | None = None) -> MethodScore:
    """Calculate Type-Token Ratio to estimate vocabulary richness."""
    body_text = (clean_text or _get_clean_text(soup)).lower()
    words = [w for w in re.findall(r"\b[a-zA-Zà-ú]{4,}\b", body_text) if w not in _STOP_WORDS]

    if len(words) < 50:
        return MethodScore(name="unique_words", label="Unique Words", max_score=5, impact="+7%")

    # TTR with sliding window of 200 words
    window = 200
    ttr_scores = []
    for i in range(0, max(len(words) - window, 1), 50):
        w = words[i : i + window]
        if w:
            ttr_scores.append(len(set(w)) / len(w))

    avg_ttr = sum(ttr_scores) / max(len(ttr_scores), 1)

    score = min(int(avg_ttr * 12), 5)

    return MethodScore(
        name="unique_words",
        label="Unique Words",
        detected=avg_ttr >= 0.40,
        score=score,
        max_score=5,
        impact="+7%",
        details={
            "ttr": round(avg_ttr, 3),
            "total_words": len(words),
            "unique_count": len(set(words)),
        },
    )


# ─── 9. Keyword Stuffing (-9%) ───────────────────────────────────────────────


def detect_keyword_stuffing(soup, clean_text: str | None = None) -> MethodScore:
    """Detect keyword stuffing that penalizes AI visibility."""
    body_text = (clean_text or _get_clean_text(soup)).lower()
    words = re.findall(r"\b[a-zA-Zà-ú]{3,}\b", body_text)

    if len(words) < 50:
        # Text too short for meaningful keyword stuffing analysis
        return MethodScore(
            name="keyword_stuffing", label="No Keyword Stuffing", score=15, max_score=15, impact="-9%", detected=False
        )

    word_freq = Counter(words)
    total = len(words)
    threshold = 0.03

    # Words with anomalous frequency (>3%)
    suspicious = {w: c for w, c in word_freq.most_common(20) if c / total > threshold and w not in _STOP_WORDS}

    stuffing_count = len(suspicious)

    # Full bonus if no stuffing detected
    if stuffing_count == 0:
        score = 15
    elif stuffing_count <= 1:
        score = 10
    elif stuffing_count <= 3:
        score = 5
    else:
        score = 0

    return MethodScore(
        name="keyword_stuffing",
        label="No Keyword Stuffing",
        detected=stuffing_count >= 2,
        score=score,
        max_score=15,
        impact="-9%",
        details={
            "suspicious_keywords": {k: round(v / total * 100, 1) for k, v in suspicious.items()},
            "stuffing_severity": "high" if stuffing_count >= 4 else "medium" if stuffing_count >= 2 else "none",
        },
    )


# ─── Orchestrator ─────────────────────────────────────────────────────────────

# Improvement suggestions for each undetected method
_IMPROVEMENT_SUGGESTIONS = {
    "quotation_addition": "Add attributed quotes in <blockquote> (+41% AI visibility)",
    "statistics_addition": "Include quantitative data: percentages, figures, metrics (+33%)",
    "fluency_optimization": "Improve fluency with longer paragraphs and logical connectives (+29%)",
    "cite_sources": "Cite authoritative sources (.edu, .gov, Wikipedia) with external links (+27%)",
    "technical_terms": "Use domain-specific technical terminology (+18%)",
    "authoritative_tone": "Add author bio with credentials and assertive tone (+16%)",
    "easy_to_understand": "Improve readability: short sentences, hierarchical headings, FAQ (+14%)",
    "unique_words": "Vary vocabulary: use synonyms, avoid repetitions (+7%)",
    "keyword_stuffing": "Reduce density of repeated keywords (-9% if present)",
}

# Order by decreasing impact (excluding keyword_stuffing which is a penalty)
_METHOD_ORDER = [
    "quotation_addition",
    "statistics_addition",
    "fluency_optimization",
    "cite_sources",
    "technical_terms",
    "authoritative_tone",
    "easy_to_understand",
    "unique_words",
    "keyword_stuffing",
]


def _compute_grade(total: int) -> str:
    """Calculate the citability grade from the total score."""
    if total >= 75:
        return "excellent"
    if total >= 50:
        return "high"
    if total >= 25:
        return "medium"
    return "low"


def audit_citability(soup, base_url: str) -> CitabilityResult:
    """Analyze content citability with all 9 Princeton methods.

    Args:
        soup: BeautifulSoup of the HTML page.
        base_url: Base URL of the site.

    Returns:
        CitabilityResult with score 0-100 and per-method detail.
    """
    # Pre-compute clean text once to avoid 3 redundant DOM re-parses (fix #190)
    clean_text = _get_clean_text(soup)

    methods = [
        detect_quotations(soup),
        detect_statistics(soup, clean_text=clean_text),
        detect_fluency(soup),
        detect_cite_sources(soup, base_url),
        detect_technical_terms(soup, clean_text=clean_text),
        detect_authoritative_tone(soup),
        detect_easy_to_understand(soup),
        detect_unique_words(soup, clean_text=clean_text),
        detect_keyword_stuffing(soup, clean_text=clean_text),
    ]

    # Sum scores (max possible = 100)
    total = sum(m.score for m in methods)
    total = max(min(total, 100), 0)

    # Top 3 improvements: undetected methods, ordered by impact
    improvements = []
    for method_name in _METHOD_ORDER:
        if method_name == "keyword_stuffing":
            continue
        method = next((m for m in methods if m.name == method_name), None)
        if method and not method.detected and method_name in _IMPROVEMENT_SUGGESTIONS:
            improvements.append(_IMPROVEMENT_SUGGESTIONS[method_name])
        if len(improvements) >= 3:
            break

    # Add stuffing warning if detected
    stuffing = next((m for m in methods if m.name == "keyword_stuffing"), None)
    if stuffing and stuffing.detected:
        improvements.insert(0, _IMPROVEMENT_SUGGESTIONS["keyword_stuffing"])

    return CitabilityResult(
        methods=methods,
        total_score=total,
        grade=_compute_grade(total),
        top_improvements=improvements[:3],
    )
