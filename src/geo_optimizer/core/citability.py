"""
Citability Score — Content analysis with 42 methods (Princeton GEO + AutoGEO + content analysis).

Each detect_*() function analyzes one aspect of HTML content and returns
a MethodScore. No ML dependencies — only regex, HTML tags and structural metrics.

Paper: "GEO: Generative Engine Optimization" (arxiv.org/abs/2311.09735)
"""

from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timezone
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


def _get_clean_text(soup, soup_clean=None) -> str:
    """Estrae testo pulito rimuovendo script, style, nav, footer.

    Args:
        soup: BeautifulSoup originale.
        soup_clean: (opzionale) soup già pulito da script/style (fix #285).
                    Se fornito, evita il re-parse costoso dell'HTML.
    """
    import copy

    if soup_clean is not None:
        # Usa copia del soup_clean pre-calcolato, rimuovi solo nav/footer/header
        working = copy.deepcopy(soup_clean)
        for tag in working(["nav", "footer", "header"]):
            tag.decompose()
        return working.get_text(separator=" ", strip=True)

    # Fallback: crea copia pulita da zero con deepcopy (fix #285: evita BS(str(soup)))
    working = copy.deepcopy(soup)
    for tag in working(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    return working.get_text(separator=" ", strip=True)


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

    score = min(authoritative_count * 2 + external_count + cite_tags * 2 + len(ref_headings) * 2, 6)
    detected = authoritative_count >= 2 or bool(ref_headings) or cite_tags >= 1

    return MethodScore(
        name="cite_sources",
        label="Cite Sources",
        detected=detected,
        score=score,
        max_score=6,
        impact="+27%",
        details={
            "authoritative_links": authoritative_count,
            "external_links": external_count,
            "cite_tags": cite_tags,
            "has_reference_section": bool(ref_headings),
        },
    )


# ─── 2. Quotation Addition (+41%) ────────────────────────────────────────────


def detect_quotations(soup, clean_text: str | None = None) -> MethodScore:
    """Detect attributed quotes (blockquote, attributed quoted text)."""
    blockquotes = soup.find_all("blockquote")
    q_tags = soup.find_all("q")

    # Blockquote with cite attribute = formal citation
    bq_with_cite = [bq for bq in blockquotes if bq.get("cite") or bq.find("cite")]

    # Text pattern "..." — Author (fix #29: usa clean_text per evitare rumore)
    body_text = clean_text or _get_clean_text(soup)
    text_attributions = _QUOTE_ATTRIBUTION_RE.findall(body_text)

    # Pull quotes (CSS class)
    pull_quotes = soup.find_all(
        ["figure", "aside", "div"],
        class_=re.compile(r"pull.?quote|blockquote|testimonial", re.I),
    )

    total = len(blockquotes) + len(q_tags) + len(text_attributions) + len(pull_quotes)
    score = min(total * 2 + len(bq_with_cite) * 2, 6)

    return MethodScore(
        name="quotation_addition",
        label="Quotation Addition",
        detected=total >= 1,
        score=score,
        max_score=6,
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

    score = min(int(density * 2) + tables_with_data * 2 + data_elements, 6)

    return MethodScore(
        name="statistics_addition",
        label="Statistics Addition",
        detected=len(matches) >= 3,
        score=score,
        max_score=6,
        impact="+33%",
        details={
            "stat_matches": len(matches),
            "density_per_1000_words": round(density, 2),
            "tables_with_data": tables_with_data,
        },
    )


# ─── 4. Fluency Optimization (+29%) ──────────────────────────────────────────


def detect_fluency(soup, clean_text: str | None = None) -> MethodScore:
    """Estimate text fluency through structural heuristics."""
    paragraphs = soup.find_all("p")
    if not paragraphs:
        return MethodScore(name="fluency_optimization", label="Fluency Optimization", max_score=6, impact="+29%")

    # Average paragraph length
    para_lengths = [len(p.get_text().split()) for p in paragraphs if p.get_text().strip()]
    avg_para_len = sum(para_lengths) / max(len(para_lengths), 1)

    # Logical connectives (fix #29: usa clean_text)
    body_text = clean_text or _get_clean_text(soup)
    connective_count = len(_CONNECTIVES.findall(body_text))

    # Text-to-list ratio
    list_items = soup.find_all("li")
    text_to_list_ratio = len(paragraphs) / max(len(list_items), 1)

    score = 0
    if avg_para_len >= 30:
        score += 2
    elif avg_para_len >= 15:
        score += 1
    score += min(connective_count // 2, 2)
    if text_to_list_ratio >= 1.5:
        score += 1
    if len(paragraphs) >= 5:
        score += 1

    return MethodScore(
        name="fluency_optimization",
        label="Fluency Optimization",
        detected=score >= 3,
        score=min(score, 6),
        max_score=6,
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

    score = min(int(density) + code_blocks * 2 + abbr_tags + dfn_tags, 5)

    return MethodScore(
        name="technical_terms",
        label="Technical Terms",
        detected=density >= 5 or code_blocks >= 1,
        score=score,
        max_score=5,
        impact="+18%",
        details={
            "tech_matches": len(tech_matches),
            "density_per_1000": round(density, 2),
            "code_blocks": code_blocks,
            "abbr_tags": abbr_tags,
        },
    )


# ─── 6. Authoritative Tone (+16%) ────────────────────────────────────────────


def detect_authoritative_tone(soup, clean_text: str | None = None) -> MethodScore:
    """Detect authoritative tone signals and author credentials."""
    body_text = clean_text or _get_clean_text(soup)

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
        score=max(min(score, 5), 0),
        max_score=5,
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
        return MethodScore(name="easy_to_understand", label="Easy-to-Understand", max_score=5, impact="+14%")

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
        score=min(score, 5),
        max_score=5,
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
        return MethodScore(name="unique_words", label="Unique Words", max_score=3, impact="+7%")

    # TTR with sliding window of 200 words
    window = 200
    ttr_scores = []
    for i in range(0, max(len(words) - window, 1), 50):
        w = words[i : i + window]
        if w:
            ttr_scores.append(len(set(w)) / len(w))

    avg_ttr = sum(ttr_scores) / max(len(ttr_scores), 1)

    score = min(int(avg_ttr * 8), 3)

    return MethodScore(
        name="unique_words",
        label="Unique Words",
        detected=avg_ttr >= 0.40,
        score=score,
        max_score=3,
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
        # Testo troppo corto per analisi significativa
        return MethodScore(
            name="keyword_stuffing", label="No Keyword Stuffing", score=6, max_score=6, impact="-9%", detected=False
        )

    word_freq = Counter(words)
    total = len(words)
    threshold = 0.03

    # Parole con frequenza anomala (>3%)
    suspicious = {w: c for w, c in word_freq.most_common(20) if c / total > threshold and w not in _STOP_WORDS}

    stuffing_count = len(suspicious)

    # Over-optimization warning (C-SEO Bench 2025):
    # 1. Frasi ripetitive (stessa frase che appare 3+ volte)
    sentences = re.split(r"[.!?]+", body_text)
    sentence_counts = Counter(s.strip() for s in sentences if len(s.strip()) > 20)
    repeated_phrases = {s: c for s, c in sentence_counts.items() if c >= 3}

    # 2. Front-loading di keyword nelle prime 200 parole
    first_200 = words[:200]
    front_loading_warning = False
    if len(first_200) >= 50:
        front_freq = Counter(first_200)
        front_total = len(first_200)
        front_suspicious = {
            w: c for w, c in front_freq.most_common(10) if c / front_total > 0.05 and w not in _STOP_WORDS
        }
        if len(front_suspicious) >= 2:
            front_loading_warning = True

    # Penalizzazione aggiuntiva per over-optimization
    over_opt_penalty = 0
    if repeated_phrases:
        over_opt_penalty += min(len(repeated_phrases), 2)
    if front_loading_warning:
        over_opt_penalty += 1

    # Punteggio pieno se nessun stuffing rilevato
    if stuffing_count == 0:
        score = 6
    elif stuffing_count <= 1:
        score = 4
    elif stuffing_count <= 3:
        score = 2
    else:
        score = 0

    # Applica penalità over-optimization
    score = max(score - over_opt_penalty, 0)

    return MethodScore(
        name="keyword_stuffing",
        label="No Keyword Stuffing",
        detected=stuffing_count >= 2 or bool(repeated_phrases),
        score=min(score, 6),
        max_score=6,
        impact="-9%",
        details={
            "suspicious_keywords": {k: round(v / total * 100, 1) for k, v in suspicious.items()},
            "stuffing_severity": "high" if stuffing_count >= 4 else "medium" if stuffing_count >= 2 else "none",
            "repeated_phrases": len(repeated_phrases),
            "front_loading_detected": front_loading_warning,
        },
    )


# ─── 10. Answer-First Structure (+25%) — AutoGEO ICLR 2026 ───────────────────


# Pattern per fatti concreti: numeri, percentuali, statement assertivi
_FACT_RE = re.compile(
    r"\b\d+(?:\.\d+)?%"  # percentuali
    r"|\$\d+"  # valute
    r"|\b\d{2,}\b"  # numeri a 2+ cifre
    r"|\b(?:is|are|was|were|has|have|can|will|must|should"
    r"|è|sono|ha|hanno|può|deve)\b",  # verbi assertivi EN+IT
    re.IGNORECASE,
)


def detect_answer_first(soup) -> MethodScore:
    """Detect answer-first structure: H2 followed by paragraph with concrete fact.

    AutoGEO (ICLR 2026) identifies AnswerFirst as one of the most effective
    strategies for AI citation. For each H2, checks if the first paragraph
    contains a concrete fact (number, assertive statement) in the first 150 chars.
    """
    h2_tags = soup.find_all("h2")
    if not h2_tags:
        return MethodScore(name="answer_first", label="Answer-First Structure", max_score=5, impact="+25%")

    answer_first_count = 0
    for h2 in h2_tags:
        # Trova il primo paragrafo dopo l'H2
        next_p = h2.find_next("p")
        if not next_p:
            continue
        # Controlla solo i primi 150 caratteri
        first_text = next_p.get_text(strip=True)[:150]
        if _FACT_RE.search(first_text):
            answer_first_count += 1

    total_h2 = len(h2_tags)
    ratio = answer_first_count / total_h2 if total_h2 > 0 else 0

    # Score proporzionale alla percentuale di H2 con answer-first
    score = min(int(ratio * 8), 5)

    return MethodScore(
        name="answer_first",
        label="Answer-First Structure",
        detected=ratio >= 0.3,
        score=score,
        max_score=5,
        impact="+25%",
        details={
            "h2_count": total_h2,
            "answer_first_count": answer_first_count,
            "ratio": round(ratio, 2),
        },
    )


# ─── 11. Passage Density (+23%) — Stanford Nature Communications 2025 ────────


def detect_passage_density(soup) -> MethodScore:
    """Detect self-contained dense passages (50-150 words with numeric data).

    Stanford Nature Communications 2025: paragraphs of 50-150 words containing
    concrete data have 2.3x citation rate compared to generic paragraphs.
    """
    paragraphs = soup.find_all("p")
    if not paragraphs:
        return MethodScore(name="passage_density", label="Passage Density", max_score=5, impact="+23%")

    total_paras = 0
    dense_paras = 0

    for p in paragraphs:
        text = p.get_text(strip=True)
        word_count = len(text.split())
        if word_count < 10:
            # Paragrafi troppo corti non contano
            continue
        total_paras += 1
        # Paragrafo denso: 50-150 parole con almeno un dato numerico
        if 50 <= word_count <= 150 and re.search(r"\b\d+(?:\.\d+)?[%$€]?|\b\d{3,}\b", text):
            dense_paras += 1

    ratio = dense_paras / total_paras if total_paras > 0 else 0

    # Score proporzionale alla percentuale di paragrafi densi
    score = min(int(ratio * 10), 5)

    return MethodScore(
        name="passage_density",
        label="Passage Density",
        detected=dense_paras >= 2,
        score=score,
        max_score=5,
        impact="+23%",
        details={
            "total_paragraphs": total_paras,
            "dense_paragraphs": dense_paras,
            "ratio": round(ratio, 2),
        },
    )


# ─── 12. Readability Score (+15%) — SE Ranking 2025 ───────────────────────────


def _count_syllables(word: str) -> int:
    """Conta sillabe approssimative in una parola inglese/italiana."""
    word = word.lower().strip()
    if len(word) <= 3:
        return 1
    # Conta gruppi vocalici come approssimazione
    vowels = "aeiouyàèéìòùü"
    count = 0
    prev_vowel = False
    for ch in word:
        is_vowel = ch in vowels
        if is_vowel and not prev_vowel:
            count += 1
        prev_vowel = is_vowel
    # Minimo 1 sillaba
    return max(count, 1)


def detect_readability(soup, clean_text: str | None = None) -> MethodScore:
    """Detect readability using Flesch-Kincaid Grade Level and section length."""
    body_text = clean_text or _get_clean_text(soup)
    words = body_text.split()
    if len(words) < 30:
        return MethodScore(name="readability", label="Readability Score", max_score=8, impact="+15%")

    # Conta frasi
    sentences = [s.strip() for s in re.split(r"[.!?]+", body_text) if len(s.strip().split()) >= 3]
    num_sentences = max(len(sentences), 1)
    num_words = len(words)

    # Conta sillabe totali
    total_syllables = sum(_count_syllables(w) for w in words)

    # Flesch-Kincaid Grade Level
    fk_grade = 0.39 * (num_words / num_sentences) + 11.8 * (total_syllables / num_words) - 15.59

    # Verifica lunghezza sezioni tra heading
    headings = soup.find_all(["h1", "h2", "h3", "h4"])
    section_lengths = []
    for _i, h in enumerate(headings):
        # Conta parole tra questo heading e il prossimo
        section_text = []
        sibling = h.find_next_sibling()
        while sibling and sibling.name not in ["h1", "h2", "h3", "h4"]:
            if sibling.name in ["p", "li", "td"]:
                section_text.append(sibling.get_text(strip=True))
            sibling = sibling.find_next_sibling()
        section_word_count = len(" ".join(section_text).split())
        if section_word_count > 0:
            section_lengths.append(section_word_count)

    # Sezioni con lunghezza ottimale (100-150 parole)
    optimal_sections = sum(1 for sl in section_lengths if 100 <= sl <= 150) if section_lengths else 0
    section_ratio = optimal_sections / max(len(section_lengths), 1)

    # Calcolo score
    score = 0

    # Sweet spot Grade 6-8: massime citazioni AI
    if 6 <= fk_grade <= 8:
        score += 5
    elif 5 <= fk_grade <= 10:
        score += 3
    elif 4 <= fk_grade <= 12:
        score += 1

    # Bonus per sezioni con lunghezza ottimale
    score += min(int(section_ratio * 3), 3)

    return MethodScore(
        name="readability",
        label="Readability Score",
        detected=6 <= fk_grade <= 10,
        score=min(score, 8),
        max_score=8,
        impact="+15%",
        details={
            "flesch_kincaid_grade": round(fk_grade, 1),
            "avg_words_per_sentence": round(num_words / num_sentences, 1),
            "avg_syllables_per_word": round(total_syllables / num_words, 2),
            "optimal_sections": optimal_sections,
            "total_sections": len(section_lengths),
        },
    )


# ─── 13. FAQ-in-Content Check (+12%) — SE Ranking 2025 ───────────────────────


def detect_faq_in_content(soup) -> MethodScore:
    """Detect FAQ patterns in content (not FAQPage schema, which has zero impact)."""
    faq_count = 0

    # Pattern 1: heading che finisce con "?" seguito da paragrafo
    for heading in soup.find_all(["h2", "h3", "h4"]):
        heading_text = heading.get_text(strip=True)
        if heading_text.endswith("?"):
            # Cerca paragrafo di risposta dopo il heading
            next_elem = heading.find_next_sibling()
            if next_elem and next_elem.name in ["p", "div", "ul", "ol"]:
                answer_text = next_elem.get_text(strip=True)
                if len(answer_text) >= 20:
                    faq_count += 1

    # Pattern 2: <details><summary> FAQ pattern
    details_elements = soup.find_all("details")
    for detail in details_elements:
        summary = detail.find("summary")
        if summary:
            summary_text = summary.get_text(strip=True)
            # Verifica che ci sia contenuto dopo il summary
            detail_text = detail.get_text(strip=True).replace(summary_text, "").strip()
            if len(detail_text) >= 20:
                faq_count += 1

    # Pattern 3: dt/dd (definition list come FAQ)
    dt_elements = soup.find_all("dt")
    for dt in dt_elements:
        dd = dt.find_next_sibling("dd")
        if dd and "?" in dt.get_text():
            faq_count += 1

    # Score basato sul numero di FAQ trovate
    if faq_count >= 5:
        score = 6
    elif faq_count >= 3:
        score = 4
    elif faq_count >= 1:
        score = 2
    else:
        score = 0

    return MethodScore(
        name="faq_in_content",
        label="FAQ-in-Content",
        detected=faq_count >= 1,
        score=min(score, 6),
        max_score=6,
        impact="+12%",
        details={
            "faq_patterns_found": faq_count,
        },
    )


# ─── 14. Image Alt Text Quality (+8%) ────────────────────────────────────────

# Pattern per alt text generici da penalizzare
_GENERIC_ALT_RE = re.compile(
    r"^(?:image|photo|picture|img|foto|immagine|screenshot|banner|icon|logo"
    r"|img\d+|image\d+|photo\d+|dsc\d+|pic\d+|untitled)$",
    re.IGNORECASE,
)


def detect_image_alt_quality(soup) -> MethodScore:
    """Detect image alt text quality: penalize missing or generic alt text."""
    images = soup.find_all("img")
    if not images:
        # Nessuna immagine = score neutro
        return MethodScore(
            name="image_alt_quality",
            label="Image Alt Quality",
            detected=False,
            score=3,
            max_score=5,
            impact="+8%",
            details={"total_images": 0, "with_alt": 0, "descriptive_alt": 0, "generic_alt": 0, "missing_alt": 0},
        )

    missing_alt = 0
    generic_alt = 0
    descriptive_alt = 0

    for img in images:
        alt = img.get("alt")
        if alt is None or alt.strip() == "":
            missing_alt += 1
        elif _GENERIC_ALT_RE.match(alt.strip()):
            generic_alt += 1
        elif len(alt.strip()) > 10:
            descriptive_alt += 1
        else:
            # Alt corto ma non generico — conta come parziale
            generic_alt += 1

    total = len(images)
    descriptive_ratio = descriptive_alt / total if total > 0 else 0

    # Score basato sulla qualità degli alt
    score = 0
    if descriptive_ratio >= 0.8:
        score = 5
    elif descriptive_ratio >= 0.5:
        score = 3
    elif descriptive_ratio >= 0.2:
        score = 2
    elif missing_alt == 0:
        score = 1

    return MethodScore(
        name="image_alt_quality",
        label="Image Alt Quality",
        detected=descriptive_ratio >= 0.5,
        score=min(score, 5),
        max_score=5,
        impact="+8%",
        details={
            "total_images": total,
            "with_alt": total - missing_alt,
            "descriptive_alt": descriptive_alt,
            "generic_alt": generic_alt,
            "missing_alt": missing_alt,
        },
    )


# ─── 15. Content Freshness Warning (+10%) ────────────────────────────────────


def detect_content_freshness(soup, clean_text: str | None = None) -> MethodScore:
    """Detect content freshness via JSON-LD dates and year references in text."""
    now = datetime.now(tz=timezone.utc)
    current_year = now.year

    # Cerca date nello schema JSON-LD
    date_modified = None
    date_published = None
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
            # Gestisci sia oggetto singolo che array
            items = data if isinstance(data, list) else [data]
            for item in items:
                if isinstance(item, dict):
                    if "dateModified" in item:
                        date_modified = item["dateModified"]
                    if "datePublished" in item:
                        date_published = item["datePublished"]
        except (json.JSONDecodeError, TypeError):
            continue

    # Cerca anche meta tag
    if not date_modified:
        meta_mod = soup.find("meta", attrs={"property": "article:modified_time"})
        if meta_mod and meta_mod.get("content"):
            date_modified = meta_mod["content"]
    if not date_published:
        meta_pub = soup.find("meta", attrs={"property": "article:published_time"})
        if meta_pub and meta_pub.get("content"):
            date_published = meta_pub["content"]

    # Analizza le date trovate
    is_fresh = False
    months_old = None
    has_date_signal = False

    for date_str in [date_modified, date_published]:
        if not date_str:
            continue
        has_date_signal = True
        # Prova a parsare la data (formato ISO)
        try:
            # Gestisci formati comuni
            clean_date = str(date_str)[:10]  # YYYY-MM-DD
            parsed = datetime.strptime(clean_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            diff = now - parsed
            months_old = diff.days / 30
            if months_old <= 6:
                is_fresh = True
            break
        except (ValueError, TypeError):
            continue

    # Cerca riferimenti ad anni nel testo
    body_text = clean_text or _get_clean_text(soup)
    year_refs = re.findall(r"\b(20[12]\d)\b", body_text)
    year_counts = Counter(year_refs)

    # Verifica se contiene anno passato senza dateModified recente
    has_old_year_refs = any(int(y) < current_year for y in year_counts)
    has_current_year_refs = any(int(y) >= current_year for y in year_counts)

    # Calcolo score
    score = 0
    warnings = []

    if is_fresh:
        score += 4
    elif has_date_signal and months_old is not None:
        if months_old <= 12:
            score += 2
        else:
            warnings.append(f"Contenuto aggiornato {int(months_old)} mesi fa")
    elif not has_date_signal:
        warnings.append("Nessun segnale di data (dateModified/datePublished) trovato")
        score += 1  # Punto base per non penalizzare troppo

    if has_current_year_refs:
        score += 2
    elif has_old_year_refs and not is_fresh:
        warnings.append("Riferimenti ad anni passati senza data di aggiornamento recente")

    return MethodScore(
        name="content_freshness",
        label="Content Freshness",
        detected=is_fresh or has_current_year_refs,
        score=min(score, 6),
        max_score=6,
        impact="+10%",
        details={
            "date_modified": date_modified,
            "date_published": date_published,
            "is_fresh": is_fresh,
            "months_old": round(months_old, 1) if months_old is not None else None,
            "year_references": dict(year_counts),
            "warnings": warnings,
        },
    )


# ─── 16. Citability Density (+15%) ───────────────────────────────────────────

# Pattern per fatti citabili: numeri, date, claim specifici (NO IGNORECASE)
_CITABLE_FACT_NUMERIC_RE = re.compile(
    r"\b\d+(?:\.\d+)?%"  # percentuali
    r"|\$\d+(?:[.,]\d+)*"  # valute $
    r"|€\d+(?:[.,]\d+)*"  # valute €
    r"|\b\d{4}\b"  # anni
    r"|\b\d+(?:\.\d+)?\s*(?:million|billion|thousand|miliardi|milioni)\b"  # grandi numeri
    r"|\b\d+(?:\.\d+)?\s*(?:x|times|volte)\b",  # moltiplicatori
    re.IGNORECASE,
)
# Nomi propri: 2-4 parole che iniziano con maiuscola (case-sensitive!)
_CITABLE_PROPER_NAME_RE = re.compile(r"(?<!\.\s)(?<!^)\b[A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,}){1,3}\b")


def detect_citability_density(soup, clean_text: str | None = None) -> MethodScore:
    """Detect density of citable facts per paragraph."""
    paragraphs = soup.find_all("p")
    if not paragraphs:
        return MethodScore(name="citability_density", label="Citability Density", max_score=7, impact="+15%")

    total_paras = 0
    dense_paras = 0
    total_facts = 0

    for p in paragraphs:
        text = p.get_text(strip=True)
        if len(text.split()) < 10:
            continue
        total_paras += 1
        numeric_facts = _CITABLE_FACT_NUMERIC_RE.findall(text)
        proper_names = _CITABLE_PROPER_NAME_RE.findall(text)
        fact_count = len(numeric_facts) + len(proper_names)
        total_facts += fact_count
        if fact_count >= 2:
            dense_paras += 1

    if total_paras == 0:
        return MethodScore(name="citability_density", label="Citability Density", max_score=7, impact="+15%")

    density_ratio = dense_paras / total_paras

    # Score basato su percentuale di paragrafi densi
    if density_ratio >= 0.5:
        score = 7
    elif density_ratio >= 0.3:
        score = 5
    elif density_ratio >= 0.15:
        score = 3
    elif dense_paras >= 1:
        score = 1
    else:
        score = 0

    return MethodScore(
        name="citability_density",
        label="Citability Density",
        detected=dense_paras >= 2,
        score=min(score, 7),
        max_score=7,
        impact="+15%",
        details={
            "total_paragraphs": total_paras,
            "dense_paragraphs": dense_paras,
            "density_ratio": round(density_ratio, 2),
            "total_citable_facts": total_facts,
        },
    )


# ─── 17. Definition Pattern Detection (+10%) ─────────────────────────────────

# Pattern per definizioni esplicite
_DEFINITION_RE = re.compile(
    r"\b(?:is|are|refers?\s+to|means?|defines?|represents?|consists?\s+of"
    r"|è|sono|si\s+riferisce\s+a|significa|definisce|rappresenta|consiste\s+in)\b",
    re.IGNORECASE,
)


def detect_definition_patterns(soup) -> MethodScore:
    """Detect definition patterns after H1/H2 headings (matches 'what is X?' queries)."""
    headings = soup.find_all(["h1", "h2"])
    if not headings:
        return MethodScore(name="definition_patterns", label="Definition Patterns", max_score=5, impact="+10%")

    definitions_found = 0

    for heading in headings:
        # Cerca il primo paragrafo dopo il heading
        next_elem = heading.find_next_sibling()
        if not next_elem:
            # Prova con find_next (potrebbe essere nested)
            next_elem = heading.find_next("p")
        if not next_elem or next_elem.name != "p":
            continue

        # Controlla i primi 150 caratteri del paragrafo
        first_text = next_elem.get_text(strip=True)[:150]
        if _DEFINITION_RE.search(first_text):
            definitions_found += 1

    total_headings = len(headings)
    ratio = definitions_found / total_headings if total_headings > 0 else 0

    # Score basato su quanti heading hanno definizione
    if ratio >= 0.6:
        score = 5
    elif ratio >= 0.4:
        score = 4
    elif ratio >= 0.2:
        score = 3
    elif definitions_found >= 1:
        score = 2
    else:
        score = 0

    return MethodScore(
        name="definition_patterns",
        label="Definition Patterns",
        detected=definitions_found >= 1,
        score=min(score, 5),
        max_score=5,
        impact="+10%",
        details={
            "definitions_found": definitions_found,
            "total_headings": total_headings,
            "ratio": round(ratio, 2),
        },
    )


# ─── 18. Response Format Mix (+8%) ───────────────────────────────────────────


def detect_format_mix(soup) -> MethodScore:
    """Detect mix of content formats: paragraphs, lists, tables."""
    has_paragraphs = len(soup.find_all("p")) >= 3
    has_lists = len(soup.find_all(["ul", "ol"])) >= 1
    has_tables = len(soup.find_all("table")) >= 1

    # Formati aggiuntivi (bonus)
    has_code = len(soup.find_all(["pre", "code"])) >= 1
    has_blockquote = len(soup.find_all("blockquote")) >= 1

    # Conta formati presenti
    base_formats = sum([has_paragraphs, has_lists, has_tables])
    bonus_formats = sum([has_code, has_blockquote])

    # Score: pieno se ha tutti e 3 i formati base
    if base_formats == 3:
        score = 4 + min(bonus_formats, 1)  # max 5
    elif base_formats == 2:
        score = 2 + min(bonus_formats, 1)  # max 3
    elif base_formats == 1:
        score = 1
    else:
        score = 0

    return MethodScore(
        name="format_mix",
        label="Response Format Mix",
        detected=base_formats >= 2,
        score=min(score, 5),
        max_score=5,
        impact="+8%",
        details={
            "has_paragraphs": has_paragraphs,
            "has_lists": has_lists,
            "has_tables": has_tables,
            "has_code": has_code,
            "has_blockquote": has_blockquote,
            "format_count": base_formats + bonus_formats,
        },
    )


# ─── 19. Attribution Completeness (+12%) — Quality Signal Batch 2 ─────────────

# Pattern per attribuzione inline: "secondo X", "according to X (2024)", etc.
_ATTRIBUTION_INLINE_RE = re.compile(
    r"\b(?:according to|as reported by|as noted by|as stated by"
    r"|secondo|come riportato da|come indicato da)\b"
    r"|(?:\w+\s+\(\d{4}\)\s+(?:found|showed|reported|demonstrated|noted|argued|claimed))",
    re.IGNORECASE,
)

# Pattern per footnote: [1], [2], numeri in apice
_FOOTNOTE_RE = re.compile(r"\[(\d{1,3})\]|\{\d{1,3}\}|<sup>\d{1,3}</sup>")


def detect_attribution(soup, clean_text: str | None = None) -> MethodScore:
    """Detect attribution completeness: inline citations, footnotes, sourced claims."""
    body_text = clean_text or _get_clean_text(soup)

    # Citazioni inline (vicine al claim)
    inline_attributions = _ATTRIBUTION_INLINE_RE.findall(body_text)

    # Link inline vicino a testo di claim (paragrafi con link + pattern autorevole)
    inline_link_citations = 0
    for p in soup.find_all("p"):
        p_text = p.get_text(strip=True)
        links_in_p = p.find_all("a", href=True)
        if links_in_p and _AUTHORITY_RE.search(p_text):
            inline_link_citations += 1

    # Footnote (fine pagina)
    raw_html = str(soup)
    footnotes = _FOOTNOTE_RE.findall(raw_html)

    # Conta sup tag con numeri (note a piè di pagina HTML)
    sup_footnotes = 0
    for sup in soup.find_all("sup"):
        sup_text = sup.get_text(strip=True)
        if sup_text.isdigit():
            sup_footnotes += 1

    total_inline = len(inline_attributions) + inline_link_citations
    total_footnotes = len(footnotes) + sup_footnotes

    # Score: inline vale di più di footnote
    score = min(total_inline * 2 + total_footnotes, 5)

    return MethodScore(
        name="attribution_completeness",
        label="Attribution Completeness",
        detected=total_inline >= 1 or total_footnotes >= 2,
        score=min(score, 5),
        max_score=5,
        impact="+12%",
        details={
            "inline_attributions": total_inline,
            "footnotes": total_footnotes,
            "inline_link_citations": inline_link_citations,
        },
    )


# ─── 20. Negative Signals Detection (-15%) — Quality Signal Batch 2 ──────────

# Pattern CTA aggressivi
_CTA_RE = re.compile(
    r"\b(?:buy now|sign up|subscribe|get started|try free|order now|click here"
    r"|compra ora|iscriviti|registrati|prova gratis|acquista|scarica ora"
    r"|limited time|act now|don't miss|offerta limitata|non perdere)\b",
    re.IGNORECASE,
)


def detect_negative_signals(soup, clean_text: str | None = None) -> MethodScore:
    """Detect negative quality signals: excessive self-promotion, thin content, repetitions."""
    body_text = clean_text or _get_clean_text(soup)
    words = body_text.split()
    word_count = len(words)
    penalties = 0

    # 1. Auto-promozione eccessiva: CTA ogni 200 parole
    cta_matches = _CTA_RE.findall(body_text)
    cta_count = len(cta_matches)
    if word_count > 0 and cta_count > 0:
        cta_ratio = word_count / max(cta_count, 1)
        if cta_ratio < 200:
            penalties += 2  # CTA troppo frequenti

    # 2. Thin content: < 300 parole con H2 complessi
    h2_tags = soup.find_all("h2")
    if h2_tags and word_count < 300:
        penalties += 2  # Contenuto troppo sottile per argomento strutturato

    # 3. Contenuto senza autore
    author_meta = soup.find("meta", attrs={"name": re.compile(r"author", re.I)})
    author_bio = soup.find_all(
        ["div", "section", "aside"],
        class_=re.compile(r"author|bio|byline", re.I),
    )
    author_schema = soup.find_all("span", attrs={"itemprop": "author"})
    if not author_meta and not author_bio and not author_schema:
        penalties += 1

    # 4. Frasi ripetitive (stessa frase 3+ volte)
    sentences = [s.strip().lower() for s in re.split(r"[.!?]+", body_text) if len(s.strip()) > 20]
    sentence_counts = Counter(sentences)
    repeated = sum(1 for c in sentence_counts.values() if c >= 3)
    if repeated > 0:
        penalties += min(repeated, 2)

    # Score INVERSO: 5 se nessun segnale, 0 se molti
    score = max(5 - penalties, 0)

    return MethodScore(
        name="no_negative_signals",
        label="No Negative Signals",
        detected=penalties >= 2,
        score=score,
        max_score=5,
        impact="-15%",
        details={
            "cta_count": cta_count,
            "is_thin_content": bool(h2_tags and word_count < 300),
            "has_author": bool(author_meta or author_bio or author_schema),
            "repeated_phrases": repeated,
            "total_penalties": penalties,
        },
    )


# ─── 21. Comparison Content (+10%) — Quality Signal Batch 2 ──────────────────

_VS_RE = re.compile(r"\bvs\.?\b|\bversus\b|\bconfronto\b|\bcomparison\b", re.IGNORECASE)
_PRO_CON_RE = re.compile(
    r"\b(?:pros?\s*(?:and|&|e)\s*cons?|vantaggi\s*e\s*svantaggi"
    r"|advantages?\s*(?:and|&)\s*disadvantages?|pro\s*e\s*contro)\b",
    re.IGNORECASE,
)


def detect_comparison_content(soup, clean_text: str | None = None) -> MethodScore:
    """Detect comparison content: tables, pro/con sections, X vs Y headings."""
    score = 0

    # 1. Pattern "X vs Y" nei heading
    vs_headings = 0
    for h in soup.find_all(["h1", "h2", "h3", "h4"]):
        h_text = h.get_text(strip=True)
        if _VS_RE.search(h_text):
            vs_headings += 1

    # 2. Sezioni pro/contro
    pro_con_sections = 0
    for h in soup.find_all(["h2", "h3", "h4"]):
        h_text = h.get_text(strip=True)
        if _PRO_CON_RE.search(h_text):
            pro_con_sections += 1
    # Cerca anche nel testo (fix #30: usa clean_text)
    body_text = clean_text or _get_clean_text(soup)
    pro_con_in_text = len(_PRO_CON_RE.findall(body_text))

    # 3. Tabelle comparative (>3 righe e >2 colonne = bonus)
    comparison_tables = 0
    large_tables = 0
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if len(rows) >= 2:
            comparison_tables += 1
            # Controlla se è "grande" (>3 righe e >2 colonne)
            cols = rows[0].find_all(["th", "td"]) if rows else []
            if len(rows) > 3 and len(cols) > 2:
                large_tables += 1

    # Calcola score
    score += min(vs_headings, 2)
    score += min(pro_con_sections + (1 if pro_con_in_text > 0 else 0), 2)
    score += min(comparison_tables + large_tables, 2)

    detected = vs_headings >= 1 or pro_con_sections >= 1 or comparison_tables >= 1

    return MethodScore(
        name="comparison_content",
        label="Comparison Content",
        detected=detected,
        score=min(score, 4),
        max_score=4,
        impact="+10%",
        details={
            "vs_headings": vs_headings,
            "pro_con_sections": pro_con_sections,
            "comparison_tables": comparison_tables,
            "large_tables": large_tables,
        },
    )


# ─── 22. E-E-A-T Composite (+15%) — Quality Signal Batch 2 ──────────────────


def detect_eeat(soup) -> MethodScore:
    """Detect E-E-A-T trust signals not covered by detect_authoritative_tone."""
    score = 0

    # Trust signals: privacy policy, terms, about, contact
    trust_links = {"privacy": False, "terms": False, "about": False, "contact": False}
    for a in soup.find_all("a", href=True):
        href = a["href"].lower()
        link_text = a.get_text(strip=True).lower()
        combined = href + " " + link_text
        if "privacy" in combined or "cookie" in combined:
            trust_links["privacy"] = True
        if "terms" in combined or "tos" in combined or "condizioni" in combined:
            trust_links["terms"] = True
        if "about" in combined or "chi-siamo" in combined or "chi siamo" in combined:
            trust_links["about"] = True
        if "contact" in combined or "contatti" in combined:
            trust_links["contact"] = True

    trust_count = sum(trust_links.values())
    score += min(trust_count, 3)

    # Experience: autore con bio dettagliata (cerchiamo pattern anno/esperienza)
    author_sections = soup.find_all(
        ["div", "section", "aside"],
        class_=re.compile(r"author|bio|about-author|byline|contributor", re.I),
    )
    has_detailed_bio = False
    for section in author_sections:
        bio_text = section.get_text(strip=True)
        # Bio dettagliata: > 50 caratteri con numeri o anni
        if len(bio_text) > 50 and re.search(r"\b\d+\s*(?:years?|anni|experience)\b", bio_text, re.I):
            has_detailed_bio = True
            break

    if has_detailed_bio:
        score += 1

    # HTTPS (cerchiamo canonical o og:url con https)
    canonical = soup.find("link", attrs={"rel": "canonical"})
    og_url = soup.find("meta", attrs={"property": "og:url"})
    is_https = False
    for tag in [canonical, og_url]:
        if tag:
            url_val = tag.get("href") or tag.get("content") or ""
            if url_val.startswith("https://"):
                is_https = True
                break
    if is_https:
        score += 1

    return MethodScore(
        name="eeat_signals",
        label="E-E-A-T Signals",
        detected=trust_count >= 2 or (has_detailed_bio and trust_count >= 1),
        score=min(score, 5),
        max_score=5,
        impact="+15%",
        details={
            "trust_links": trust_links,
            "trust_link_count": trust_count,
            "has_detailed_bio": has_detailed_bio,
            "is_https": is_https,
        },
    )


# ─── 23. Content Decay Detection (-10%) — Quality Signal Batch 2 ─────────────


def detect_content_decay(soup, clean_text: str | None = None) -> MethodScore:
    """Detect content decay signals: old year references, stale update dates."""
    body_text = clean_text or _get_clean_text(soup)
    now = datetime.now(tz=timezone.utc)
    current_year = now.year
    penalties = 0

    # 1. Anni passati nel testo senza dateModified recente
    year_refs = re.findall(r"\b(20[12]\d)\b", body_text)
    old_years = [int(y) for y in year_refs if int(y) < current_year - 1]
    current_years = [int(y) for y in year_refs if int(y) >= current_year]

    # Controlla dateModified
    date_modified = None
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
            items = data if isinstance(data, list) else [data]
            for item in items:
                if isinstance(item, dict) and "dateModified" in item:
                    date_modified = item["dateModified"]
        except (json.JSONDecodeError, TypeError):
            continue
    if not date_modified:
        meta_mod = soup.find("meta", attrs={"property": "article:modified_time"})
        if meta_mod and meta_mod.get("content"):
            date_modified = meta_mod["content"]

    # Verifica se dateModified è recente
    is_recently_modified = False
    if date_modified:
        try:
            clean_date = str(date_modified)[:10]
            parsed = datetime.strptime(clean_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            months_old = (now - parsed).days / 30
            is_recently_modified = months_old <= 12
        except (ValueError, TypeError):
            pass

    # Penalizza anni vecchi senza aggiornamento recente
    if old_years and not is_recently_modified and not current_years:
        penalties += min(len(set(old_years)), 3)

    # 2. Pattern "last updated" / "aggiornato" con data vecchia
    update_patterns = re.findall(
        r"(?:last\s+updated|updated\s+on|aggiornato\s+(?:il|a|al))\s*:?\s*"
        r"(?:(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})|(\w+)\s+(\d{1,2}),?\s+(\d{4}))",
        body_text,
        re.IGNORECASE,
    )
    for match in update_patterns:
        # Estrai l'anno dal match
        year_str = match[2] or match[5]
        if year_str and int(year_str) < current_year - 1:
            penalties += 1

    # 3. Conta link esterni (non possiamo testare se rotti, ma segnaliamo quantità)
    external_links = 0
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith("http") and not href.startswith("#"):
            external_links += 1

    # Score INVERSO: 5 se nessun decay, 0 se molto
    score = max(5 - penalties, 0)

    return MethodScore(
        name="no_content_decay",
        label="No Content Decay",
        detected=penalties >= 2,
        score=score,
        max_score=5,
        impact="-10%",
        details={
            "old_year_references": list(set(old_years)),
            "is_recently_modified": is_recently_modified,
            "stale_update_patterns": len(update_patterns),
            "external_links_count": external_links,
            "total_penalties": penalties,
        },
    )


# ─── 24. Content-to-Boilerplate Ratio (+8%) — Quality Signal Batch 2 ─────────


def detect_boilerplate_ratio(soup, soup_clean=None) -> MethodScore:
    """Detect content-to-boilerplate ratio: main/article text vs total page text."""
    import copy

    # Fix #4: usa soup_clean pre-calcolato se disponibile
    if soup_clean is not None:
        total_soup = soup_clean
    else:
        total_soup = copy.deepcopy(soup)
        for tag in total_soup(["script", "style"]):
            tag.decompose()
    total_text = total_soup.get_text(separator=" ", strip=True)
    total_len = len(total_text)

    if total_len < 50:
        return MethodScore(
            name="boilerplate_ratio",
            label="Content-to-Boilerplate Ratio",
            detected=False,
            score=2,
            max_score=4,
            impact="+8%",
            details={"ratio": 0, "method": "insufficient_text"},
        )

    # Cerca contenuto principale in <main> o <article>
    content_tag = soup.find("main") or soup.find("article")
    method = "main_tag"

    if content_tag:
        content_text = content_tag.get_text(separator=" ", strip=True)
    else:
        # Euristica: rimuovi nav, header, footer, sidebar
        method = "heuristic"
        clean_soup = copy.deepcopy(soup)
        for tag in clean_soup(["script", "style", "nav", "header", "footer"]):
            tag.decompose()
        # Rimuovi sidebar per class/id
        for tag in clean_soup.find_all(
            ["div", "aside", "section"],
            class_=re.compile(r"sidebar|widget|menu|navigation|nav-", re.I),
        ):
            tag.decompose()
        for tag in clean_soup.find_all(
            ["div", "aside", "section"],
            id=re.compile(r"sidebar|widget|menu|navigation", re.I),
        ):
            tag.decompose()
        content_text = clean_soup.get_text(separator=" ", strip=True)

    content_len = len(content_text)
    ratio = content_len / total_len if total_len > 0 else 0

    # Score basato sul rapporto
    if ratio >= 0.6:
        score = 4
    elif ratio >= 0.45:
        score = 3
    elif ratio >= 0.30:
        score = 2
    elif ratio >= 0.15:
        score = 1
    else:
        score = 0

    return MethodScore(
        name="boilerplate_ratio",
        label="Content-to-Boilerplate Ratio",
        detected=ratio >= 0.45,
        score=min(score, 4),
        max_score=4,
        impact="+8%",
        details={
            "content_length": content_len,
            "total_length": total_len,
            "ratio": round(ratio, 2),
            "method": method,
        },
    )


# ─── 25. Nuance/Honesty Signals (+5%) — Quality Signal Batch 2 ──────────────

_NUANCE_RE = re.compile(
    r"\b(?:however|on the other hand|nevertheless|nonetheless|that said"
    r"|conversely|in contrast|although|despite|while .+ also"
    r"|limitations? include|drawbacks?|disadvantages?"
    r"|it(?:'s| is) (?:worth noting|important to note)"
    r"|not without|trade-?offs?|caveat|downside"
    r"|tuttavia|d'altra parte|nonostante|ciononostante"
    r"|limiti|svantaggi|aspetti negativi)\b",
    re.IGNORECASE,
)

_NUANCE_HEADING_RE = re.compile(
    r"\b(?:limitations?|cons|disadvantages?|drawbacks?|challenges?"
    r"|trade-?offs?|caveats?|risks?"
    r"|limiti|svantaggi|sfide|rischi)\b",
    re.IGNORECASE,
)


def detect_nuance_signals(soup, clean_text: str | None = None) -> MethodScore:
    """Detect nuance and intellectual honesty signals in content."""
    body_text = clean_text or _get_clean_text(soup)

    # Pattern di onestà nel testo
    nuance_matches = _NUANCE_RE.findall(body_text)

    # Heading con sezioni dedicate a limitazioni/svantaggi
    nuance_headings = 0
    for h in soup.find_all(["h2", "h3", "h4"]):
        h_text = h.get_text(strip=True)
        if _NUANCE_HEADING_RE.search(h_text):
            nuance_headings += 1

    total_signals = len(nuance_matches) + nuance_headings * 2

    # Score basato sulla quantità di segnali
    if total_signals >= 5:
        score = 3
    elif total_signals >= 3:
        score = 2
    elif total_signals >= 1:
        score = 1
    else:
        score = 0

    return MethodScore(
        name="nuance_signals",
        label="Nuance/Honesty Signals",
        detected=total_signals >= 2,
        score=min(score, 3),
        max_score=3,
        impact="+5%",
        details={
            "nuance_patterns": len(nuance_matches),
            "nuance_headings": nuance_headings,
            "total_signals": total_signals,
        },
    )


# ─── 26. Snippet-Ready / Zero-Click (#249) ────────────────────────────────────

# Pattern per definizioni esplicite nei primi 150 char dopo heading
_SNIPPET_DEF_RE = re.compile(
    r"\b(?:is|are|refers?\s+to|means?|can\s+be\s+defined\s+as"
    r"|è|sono|si\s+riferisce\s+a|significa)\b",
    re.IGNORECASE,
)


def detect_snippet_ready(soup) -> MethodScore:
    """Detect zero-click / snippet-ready content sections.

    Checks if headings are followed by concise definitions (first 150 chars)
    or if question headings (ending with '?') have direct answers under 60 words.
    """
    headings = soup.find_all(["h2", "h3", "h4"])
    if not headings:
        return MethodScore(name="snippet_ready", label="Snippet-Ready Content", max_score=4, impact="+10%")

    snippet_ready_count = 0

    for heading in headings:
        heading_text = heading.get_text(strip=True)
        # Trova il primo paragrafo dopo il heading
        next_p = heading.find_next("p")
        if not next_p:
            continue
        p_text = next_p.get_text(strip=True)

        # Pattern 1: heading con "?" → risposta diretta sotto 60 parole
        if heading_text.endswith("?"):
            word_count = len(p_text.split())
            if 5 <= word_count <= 60:
                snippet_ready_count += 1
                continue

        # Pattern 2: definizione esplicita nei primi 150 char dopo heading
        first_150 = p_text[:150]
        if _SNIPPET_DEF_RE.search(first_150):
            snippet_ready_count += 1

    total_headings = len(headings)
    ratio = snippet_ready_count / total_headings if total_headings > 0 else 0

    # Score proporzionale
    if ratio >= 0.5:
        score = 4
    elif ratio >= 0.3:
        score = 3
    elif ratio >= 0.15:
        score = 2
    elif snippet_ready_count >= 1:
        score = 1
    else:
        score = 0

    return MethodScore(
        name="snippet_ready",
        label="Snippet-Ready Content",
        detected=snippet_ready_count >= 1,
        score=min(score, 4),
        max_score=4,
        impact="+10%",
        details={
            "snippet_ready_sections": snippet_ready_count,
            "total_headings": total_headings,
            "ratio": round(ratio, 2),
        },
    )


# ─── 27. Chunk Quotability (#229) ────────────────────────────────────────────

# Fix #7: rimossa _CONCRETE_DATA_RE duplicata — usa _CITABLE_FACT_NUMERIC_RE


def detect_chunk_quotability(soup) -> MethodScore:
    """Detect quotable content chunks: self-contained paragraphs with concrete data.

    For each paragraph of 50-150 words, checks if it contains concrete data
    (numbers, percentages, dates) making it independently quotable by AI.
    """
    paragraphs = soup.find_all("p")
    if not paragraphs:
        return MethodScore(name="chunk_quotability", label="Chunk Quotability", max_score=4, impact="+10%")

    candidate_count = 0
    quotable_count = 0

    for p in paragraphs:
        text = p.get_text(strip=True)
        word_count = len(text.split())
        # Solo paragrafi nella fascia 50-150 parole
        if word_count < 50 or word_count > 150:
            continue
        candidate_count += 1
        # Verifica dato concreto
        if _CITABLE_FACT_NUMERIC_RE.search(text):  # fix #7: regex unificata
            quotable_count += 1

    ratio = quotable_count / candidate_count if candidate_count > 0 else 0

    # Score proporzionale alla % di paragrafi quotabili
    if ratio >= 0.5:
        score = 4
    elif ratio >= 0.3:
        score = 3
    elif ratio >= 0.15:
        score = 2
    elif quotable_count >= 1:
        score = 1
    else:
        score = 0

    return MethodScore(
        name="chunk_quotability",
        label="Chunk Quotability",
        detected=quotable_count >= 1,
        score=min(score, 4),
        max_score=4,
        impact="+10%",
        details={
            "candidate_paragraphs": candidate_count,
            "quotable_paragraphs": quotable_count,
            "ratio": round(ratio, 2),
        },
    )


# ─── 28. Blog Structure (#230) ───────────────────────────────────────────────


def detect_blog_structure(soup) -> MethodScore:
    """Detect blog structure signals in Article/BlogPosting schema.

    Checks: datePublished/dateModified, author bio, categories/tags.
    Only scores if Article or BlogPosting schema is present (non-blog pages get 0).
    """
    # Cerca schema Article o BlogPosting nel JSON-LD
    article_schema = None
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
            items = data if isinstance(data, list) else [data]
            for item in items:
                if isinstance(item, dict):
                    schema_type = item.get("@type", "")
                    types = schema_type if isinstance(schema_type, list) else [schema_type]
                    if any(t in ("Article", "BlogPosting", "NewsArticle") for t in types):
                        article_schema = item
                        break
        except (json.JSONDecodeError, TypeError):
            continue
        if article_schema:
            break

    # Se non c'è schema Article/BlogPosting, score 0 senza penalizzare
    if not article_schema:
        return MethodScore(
            name="blog_structure",
            label="Blog Structure",
            detected=False,
            score=0,
            max_score=4,
            impact="+8%",
            details={"has_article_schema": False},
        )

    score = 0
    has_dates = bool(article_schema.get("datePublished") or article_schema.get("dateModified"))
    has_author = bool(article_schema.get("author"))
    # Cerca categorie/tag nei meta o nello schema
    has_categories = bool(
        article_schema.get("articleSection")
        or article_schema.get("keywords")
        or soup.find("meta", attrs={"property": "article:tag"})
    )
    # Cerca author bio nel DOM
    author_bio = soup.find_all(
        ["div", "section", "aside"],
        class_=re.compile(r"author|bio|about-author|byline", re.I),
    )
    has_author_bio = bool(author_bio)

    if has_dates:
        score += 1
    if has_author:
        score += 1
    if has_author_bio:
        score += 1
    if has_categories:
        score += 1

    return MethodScore(
        name="blog_structure",
        label="Blog Structure",
        detected=score >= 2,
        score=min(score, 4),
        max_score=4,
        impact="+8%",
        details={
            "has_article_schema": True,
            "has_dates": has_dates,
            "has_author": has_author,
            "has_author_bio": has_author_bio,
            "has_categories": has_categories,
        },
    )


# ─── 29. AI Shopping Readiness (#277) ────────────────────────────────────────


def detect_shopping_readiness(soup) -> MethodScore:
    """Detect AI shopping readiness from Product schema.

    Checks: Product schema with price + availability, AggregateRating, review count.
    Only scores if Product schema is present (non-ecommerce pages get 0).
    """
    product_schema = None
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
            items = data if isinstance(data, list) else [data]
            for item in items:
                if isinstance(item, dict):
                    schema_type = item.get("@type", "")
                    types = schema_type if isinstance(schema_type, list) else [schema_type]
                    if "Product" in types:
                        product_schema = item
                        break
        except (json.JSONDecodeError, TypeError):
            continue
        if product_schema:
            break

    if not product_schema:
        return MethodScore(
            name="shopping_readiness",
            label="AI Shopping Readiness",
            detected=False,
            score=0,
            max_score=3,
            impact="+8%",
            details={"has_product_schema": False},
        )

    score = 0
    # Verifica price + availability nell'offerta
    offers = product_schema.get("offers") or product_schema.get("offer", {})
    if isinstance(offers, list):
        offers = offers[0] if offers else {}
    has_price = bool(offers.get("price") or offers.get("lowPrice"))
    has_availability = bool(offers.get("availability"))

    if has_price and has_availability:
        score += 1

    # AggregateRating
    has_rating = bool(product_schema.get("aggregateRating"))
    if has_rating:
        score += 1

    # Review count
    rating_data = product_schema.get("aggregateRating", {})
    has_review_count = bool(rating_data.get("reviewCount") or rating_data.get("ratingCount"))
    if has_review_count:
        score += 1

    return MethodScore(
        name="shopping_readiness",
        label="AI Shopping Readiness",
        detected=score >= 1,
        score=min(score, 3),
        max_score=3,
        impact="+8%",
        details={
            "has_product_schema": True,
            "has_price": has_price,
            "has_availability": has_availability,
            "has_rating": has_rating,
            "has_review_count": has_review_count,
        },
    )


# ─── 30. ChatGPT Shopping Feed (#275) ────────────────────────────────────────


def detect_chatgpt_shopping(soup) -> MethodScore:
    """Detect ChatGPT Shopping integration signals from Product schema.

    Checks required fields for ChatGPT Shopping: name, price, image, availability, brand.
    Cannot verify chatgpt.com/merchants registration, but verifies field completeness.
    """
    product_schema = None
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
            items = data if isinstance(data, list) else [data]
            for item in items:
                if isinstance(item, dict):
                    schema_type = item.get("@type", "")
                    types = schema_type if isinstance(schema_type, list) else [schema_type]
                    if "Product" in types:
                        product_schema = item
                        break
        except (json.JSONDecodeError, TypeError):
            continue
        if product_schema:
            break

    if not product_schema:
        return MethodScore(
            name="chatgpt_shopping",
            label="ChatGPT Shopping Feed",
            detected=False,
            score=0,
            max_score=3,
            impact="+8%",
            details={"has_product_schema": False},
        )

    # Campi richiesti per ChatGPT Shopping
    has_name = bool(product_schema.get("name"))
    has_image = bool(product_schema.get("image"))
    has_brand = bool(product_schema.get("brand"))

    offers = product_schema.get("offers") or product_schema.get("offer", {})
    if isinstance(offers, list):
        offers = offers[0] if offers else {}
    has_price = bool(offers.get("price") or offers.get("lowPrice"))
    has_availability = bool(offers.get("availability"))

    # Conta campi presenti su 5 richiesti
    fields_present = sum([has_name, has_image, has_brand, has_price, has_availability])

    if fields_present >= 5:
        score = 3
    elif fields_present >= 3:
        score = 2
    elif fields_present >= 1:
        score = 1
    else:
        score = 0

    return MethodScore(
        name="chatgpt_shopping",
        label="ChatGPT Shopping Feed",
        detected=fields_present >= 3,
        score=min(score, 3),
        max_score=3,
        impact="+8%",
        details={
            "has_product_schema": True,
            "has_name": has_name,
            "has_image": has_image,
            "has_brand": has_brand,
            "has_price": has_price,
            "has_availability": has_availability,
            "fields_present": fields_present,
            "fields_required": 5,
        },
    )


# ─── Voice/Conversational Search (+5%) — Batch A v3.16.0 ─────────────────────

# Pattern per heading in formato domanda naturale (EN + IT)
_QUESTION_HEADING_RE = re.compile(
    r"^(?:how\s+(?:do|can|to|does)|what\s+is|what\s+are|why\s+(?:do|is|are|does)"
    r"|when\s+(?:do|is|should)|where\s+(?:do|can|is)|which\s+(?:is|are)"
    r"|come\s+(?:funziona|fare|si)|cosa\s+(?:è|sono)|perché\s+(?:è|si)"
    r"|qual\s+è|quali\s+sono|quando\s+(?:è|si))",
    re.IGNORECASE,
)


def detect_voice_search(soup) -> MethodScore:
    """Detect voice/conversational search readiness signals."""
    score = 0
    question_headings = 0
    concise_answers = 0
    has_speakable = False

    # 1. Cerca heading in formato domanda naturale
    headings = soup.find_all(re.compile(r"^h[1-6]$", re.I))
    for h in headings:
        text = h.get_text(strip=True)
        if "?" in text or _QUESTION_HEADING_RE.search(text):
            question_headings += 1
            # Cerca risposta concisa dopo heading con "?"
            if "?" in text:
                next_p = h.find_next("p")
                if next_p:
                    words = next_p.get_text(strip=True).split()
                    if 0 < len(words) < 60:
                        concise_answers += 1

    if question_headings >= 2:
        score += 1
    if concise_answers >= 1:
        score += 1

    # 2. Cerca speakable schema in qualsiasi JSON-LD
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
            items = data if isinstance(data, list) else [data]
            for item in items:
                if isinstance(item, dict) and "speakable" in item:
                    has_speakable = True
                    break
        except (json.JSONDecodeError, TypeError):
            continue
        if has_speakable:
            break

    if has_speakable:
        score += 1

    return MethodScore(
        name="voice_search_ready",
        label="Voice/Conversational Search",
        detected=question_headings >= 2 or has_speakable,
        score=min(score, 3),
        max_score=3,
        impact="+5%",
        details={
            "question_headings": question_headings,
            "concise_answers": concise_answers,
            "has_speakable_schema": has_speakable,
        },
    )


# ─── Multi-Platform Presence (+10%) — Batch A v3.16.0 ────────────────────────

# Piattaforme riconosciute per multi-platform presence
_PLATFORM_DOMAINS = {
    "github.com": "GitHub",
    "linkedin.com": "LinkedIn",
    "twitter.com": "Twitter/X",
    "x.com": "Twitter/X",
    "youtube.com": "YouTube",
    "reddit.com": "Reddit",
    "wikipedia.org": "Wikipedia",
    "medium.com": "Medium",
    "facebook.com": "Facebook",
}


def detect_multi_platform(soup) -> MethodScore:
    """Detect multi-platform presence via sameAs URLs in schema."""
    platforms_found: set[str] = set()

    # Estrai sameAs da tutti gli schema JSON-LD
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
            items = data if isinstance(data, list) else [data]
            for item in items:
                if not isinstance(item, dict):
                    continue
                same_as = item.get("sameAs", [])
                if isinstance(same_as, str):
                    same_as = [same_as]
                for url in same_as:
                    if not isinstance(url, str):
                        continue
                    parsed = urlparse(url)
                    domain = parsed.netloc.lower().removeprefix("www.")
                    for plat_domain, plat_name in _PLATFORM_DOMAINS.items():
                        if domain.endswith(plat_domain):
                            platforms_found.add(plat_name)
        except (json.JSONDecodeError, TypeError):
            continue

    count = len(platforms_found)
    if count >= 5:
        score = 4
    elif count >= 3:
        score = 2
    else:
        score = 0

    return MethodScore(
        name="multi_platform",
        label="Multi-Platform Presence",
        detected=count >= 3,
        score=min(score, 4),
        max_score=4,
        impact="+10%",
        details={
            "platforms_found": sorted(platforms_found),
            "platform_count": count,
        },
    )


# ─── Entity Disambiguation (+8%) — Batch A v3.16.0 ───────────────────────────


def detect_entity_disambiguation(soup) -> MethodScore:
    """Detect entity disambiguation signals: consistent naming and explicit definitions."""
    score = 0

    # 1. Raccogli nomi dal title, og:title, schema name
    names: list[str] = []
    title_tag = soup.find("title")
    if title_tag and title_tag.string:
        # Prendi la parte prima di separatori comuni
        raw = title_tag.string.strip()
        parts = re.split(r"\s*[|\-–—]\s*", raw)
        if parts:
            names.append(parts[0].strip().lower())

    og_title = soup.find("meta", attrs={"property": "og:title"})
    if og_title and og_title.get("content"):
        parts = re.split(r"\s*[|\-–—]\s*", og_title["content"])
        if parts:
            names.append(parts[0].strip().lower())

    # Nome dallo schema JSON-LD
    schema_name = None
    sameas_count = 0
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
            items = data if isinstance(data, list) else [data]
            for item in items:
                if isinstance(item, dict):
                    if "name" in item and not schema_name:
                        schema_name = str(item["name"]).strip().lower()
                        names.append(schema_name)
                    same_as = item.get("sameAs", [])
                    if isinstance(same_as, str):
                        same_as = [same_as]
                    if isinstance(same_as, list):
                        sameas_count = max(sameas_count, len(same_as))
        except (json.JSONDecodeError, TypeError):
            continue

    # Verifica consistenza: almeno 2 nomi e tutti uguali
    if len(names) >= 2:
        unique_names = set(names)
        if len(unique_names) == 1:
            score += 1

    # 2. Prima frase contiene definizione esplicita del brand/sito
    body = soup.find("body")
    if body:
        # Cerca il primo paragrafo significativo
        first_p = body.find("p")
        if first_p:
            first_text = first_p.get_text(strip=True)
            # Cerca pattern definitorio: "X is...", "X è..."
            if re.search(r"\b(?:is|are|è|sono)\s+(?:a|an|the|un|una|il|la|lo)\b", first_text, re.I):
                score += 1

    # 3. sameAs con > 3 link (bonus disambiguazione)
    if sameas_count > 3:
        score += 1

    return MethodScore(
        name="entity_disambiguation",
        label="Entity Disambiguation",
        detected=score >= 2,
        score=min(score, 3),
        max_score=3,
        impact="+8%",
        details={
            "names_found": names,
            "names_consistent": len(set(names)) <= 1 if names else False,
            "sameas_count": sameas_count,
        },
    )


# ─── First-Party Data (+12%) — Batch A v3.16.0 ──────────────────────────────

# Pattern per dati di prima parte
_FIRST_PARTY_PATTERNS = re.compile(
    r"\b(?:our\s+research|we\s+analyzed|our\s+data\s+shows?"
    r"|our\s+study|we\s+found|our\s+analysis|we\s+discovered"
    r"|we\s+tested|our\s+findings|we\s+measured"
    r"|la\s+nostra\s+ricerca|abbiamo\s+analizzato|i\s+nostri\s+dati)\b",
    re.IGNORECASE,
)

# Pattern per numeri specifici attribuiti al sito (non citazioni esterne)
_OWN_DATA_RE = re.compile(
    r"\b(?:we|our\s+team|our\s+company)\s+\w+\s+\d+",
    re.IGNORECASE,
)


def detect_first_party_data(soup, clean_text: str | None = None) -> MethodScore:
    """Detect first-party data and original research signals."""
    body_text = clean_text or _get_clean_text(soup)
    score = 0

    # 1. Pattern di ricerca propria
    first_party_matches = _FIRST_PARTY_PATTERNS.findall(body_text)
    if len(first_party_matches) >= 2:
        score += 2
    elif len(first_party_matches) >= 1:
        score += 1

    # 2. Numeri specifici attribuiti al sito stesso
    own_data_matches = _OWN_DATA_RE.findall(body_text)
    if own_data_matches:
        score += 1

    # 3. Sezione "Methodology" o "Methods"
    has_methodology = False
    for h in soup.find_all(re.compile(r"^h[1-6]$", re.I)):
        h_text = h.get_text(strip=True).lower()
        if h_text in (
            "methodology",
            "methods",
            "our methodology",
            "research methodology",
            "metodologia",
            "metodo",
            "la nostra metodologia",
        ):
            has_methodology = True
            break
    if has_methodology:
        score += 1

    return MethodScore(
        name="first_party_data",
        label="First-Party Data",
        detected=score >= 2,
        score=min(score, 4),
        max_score=4,
        impact="+12%",
        details={
            "first_party_patterns": len(first_party_matches),
            "own_data_signals": len(own_data_matches),
            "has_methodology_section": has_methodology,
        },
    )


# ─── Stale Data Detection (-10%) — Batch A v3.16.0 ──────────────────────────


def detect_stale_data(soup, clean_text: str | None = None) -> MethodScore:
    """Detect stale data signals. Score INVERSO: 4 se pulito, 0 se molto stale."""
    body_text = clean_text or _get_clean_text(soup)
    now = datetime.now(tz=timezone.utc)
    current_year = now.year
    penalties = 0

    # 1. Copyright anno vecchio nel footer
    footer = soup.find("footer")
    old_copyright = False
    if footer:
        footer_text = footer.get_text(strip=True)
        copyright_years = re.findall(r"©\s*(20\d{2})|copyright\s*(20\d{2})", footer_text, re.I)
        for match in copyright_years:
            year = int(match[0] or match[1])
            if year < current_year - 1:
                old_copyright = True
                penalties += 2
                break

    # 2. Pattern "as of YYYY" o "in YYYY" con anno stale nel testo
    stale_refs = re.findall(
        r"\b(?:as\s+of|in|nel|del|aggiornato\s+al?)\s+(20[12]\d)\b",
        body_text,
        re.IGNORECASE,
    )
    stale_year_refs = [int(y) for y in stale_refs if int(y) < current_year - 1]
    if len(stale_year_refs) >= 3:
        penalties += 2
    elif len(stale_year_refs) >= 1:
        penalties += 1

    # Score inverso: 4 se pulito, 0 se molto stale
    score = max(4 - penalties, 0)

    return MethodScore(
        name="no_stale_data",
        label="No Stale Data",
        detected=penalties == 0,
        score=min(score, 4),
        max_score=4,
        impact="-10%",
        details={
            "old_copyright_in_footer": old_copyright,
            "stale_year_references": stale_year_refs,
            "penalties": penalties,
        },
    )


# ─── Social Proof (+8%) — Batch A v3.16.0 ────────────────────────────────────


def detect_social_proof(soup, clean_text: str | None = None) -> MethodScore:
    """Detect social proof signals: testimonials, ratings, trust badges."""
    score = 0

    # 1. Testimonial: class="testimonial", blockquote con nome, "as seen in"
    has_testimonial = False
    testimonial_divs = soup.find_all(
        ["div", "section", "aside"],
        class_=re.compile(r"testimonial|review|customer-quote", re.I),
    )
    if testimonial_divs:
        has_testimonial = True

    # Blockquote con attribuzione (nome persona)
    blockquotes = soup.find_all("blockquote")
    for bq in blockquotes:
        # Cerca cite o footer dentro blockquote
        cite = bq.find(["cite", "footer", "figcaption"])
        if cite:
            has_testimonial = True
            break

    # Pattern "as seen in" / "as featured in"
    body_text = clean_text or _get_clean_text(soup)
    if re.search(r"\b(?:as\s+seen\s+in|as\s+featured\s+in|featured\s+by|trusted\s+by)\b", body_text, re.I):
        has_testimonial = True

    if has_testimonial:
        score += 1

    # 2. AggregateRating nel schema con reviewCount > 10
    has_rating = False
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
            items = data if isinstance(data, list) else [data]
            for item in items:
                if isinstance(item, dict):
                    rating = item.get("aggregateRating", {})
                    if isinstance(rating, dict):
                        review_count = int(rating.get("reviewCount", 0))
                        if review_count > 10:
                            has_rating = True
        except (json.JSONDecodeError, TypeError, ValueError):
            continue

    if has_rating:
        score += 1

    # 3. Trust badges, partner logos
    has_trust_badges = False
    badge_imgs = soup.find_all(
        "img",
        attrs={
            "alt": re.compile(r"badge|certified|partner|award|trust|seal|logo", re.I),
        },
    )
    if badge_imgs:
        has_trust_badges = True

    # Sezione trust/partner
    trust_sections = soup.find_all(
        ["div", "section"],
        class_=re.compile(r"partner|trust|badge|certified|award|client-logo", re.I),
    )
    if trust_sections:
        has_trust_badges = True

    if has_trust_badges:
        score += 1

    return MethodScore(
        name="social_proof",
        label="Social Proof",
        detected=score >= 1,
        score=min(score, 3),
        max_score=3,
        impact="+8%",
        details={
            "has_testimonial": has_testimonial,
            "has_aggregate_rating": has_rating,
            "has_trust_badges": has_trust_badges,
        },
    )


# ─── Accessibility as Signal (+5%) — Batch A v3.16.0 ─────────────────────────


def detect_accessibility_signals(soup) -> MethodScore:
    """Detect accessibility signals: semantic HTML, ARIA landmarks, skip links."""
    score = 0

    # 1. Semantic HTML tags
    semantic_tags = {"main", "nav", "header", "footer"}
    found_semantic = set()
    for tag_name in semantic_tags:
        if soup.find(tag_name):
            found_semantic.add(tag_name)

    if len(found_semantic) >= 3:
        score += 1

    # 2. ARIA landmarks
    aria_roles = {"main", "navigation", "banner", "contentinfo"}
    found_aria = set()
    for role in aria_roles:
        if soup.find(attrs={"role": role}):
            found_aria.add(role)

    if found_aria:
        score += 1

    # 3. Skip link
    has_skip_link = False
    for a in soup.find_all("a", href=True):
        href = a["href"].lower()
        if href in ("#main", "#content", "#main-content", "#maincontent"):
            has_skip_link = True
            break
        # Cerca anche testo "skip to"
        link_text = a.get_text(strip=True).lower()
        if "skip to" in link_text or "vai al contenuto" in link_text:
            has_skip_link = True
            break

    if has_skip_link:
        score += 1

    return MethodScore(
        name="accessibility_signals",
        label="Accessibility Signals",
        detected=score >= 1,
        score=min(score, 3),
        max_score=3,
        impact="+5%",
        details={
            "semantic_tags": sorted(found_semantic),
            "aria_landmarks": sorted(found_aria),
            "has_skip_link": has_skip_link,
        },
    )


# ─── AI Conversion Funnel (+8%) — Batch A v3.16.0 ────────────────────────────

# Pattern CTA positivi per conversion funnel (fix #25: rinominata per non sovrascrivere _CTA_RE aggressivi)
_CTA_FUNNEL_RE = re.compile(
    r"\b(?:try\s+(?:it\s+)?(?:free|now)|start\s+(?:free|now|your)"
    r"|sign\s+up|get\s+started|request\s+(?:a\s+)?demo"
    r"|free\s+trial|book\s+(?:a\s+)?demo|inizia\s+(?:ora|gratis)"
    r"|provalo?\s+(?:gratis|ora)|registrati)\b",
    re.IGNORECASE,
)


def detect_conversion_funnel(soup) -> MethodScore:
    """Detect AI conversion funnel signals: CTAs, pricing links, contact info."""
    score = 0

    # 1. CTA visibile (bottone/link con pattern CTA)
    has_cta = False
    for tag in soup.find_all(["a", "button"]):
        text = tag.get_text(strip=True)
        if _CTA_FUNNEL_RE.search(text):
            has_cta = True
            break

    if has_cta:
        score += 1

    # 2. Pricing page link
    has_pricing = False
    for a in soup.find_all("a", href=True):
        href = a["href"].lower()
        if "pricing" in href or "plans" in href or "prezzi" in href:
            has_pricing = True
            break

    if has_pricing:
        score += 1

    # 3. Contatto (href con "contact", "mailto:")
    has_contact = False
    for a in soup.find_all("a", href=True):
        href = a["href"].lower()
        if "contact" in href or "mailto:" in href or "contatti" in href:
            has_contact = True
            break

    if has_contact:
        score += 1

    return MethodScore(
        name="conversion_funnel",
        label="AI Conversion Funnel",
        detected=score >= 1,
        score=min(score, 3),
        max_score=3,
        impact="+8%",
        details={
            "has_cta": has_cta,
            "has_pricing_link": has_pricing,
            "has_contact": has_contact,
        },
    )


# ─── Temporal Signal Coherence (+8%) — Batch B v3.16.0 ───────────────────────

# Pattern per date nel testo: "Last updated: DATE", "Updated: DATE", etc.
_UPDATED_DATE_RE = re.compile(
    r"\b(?:last\s+updated|updated|aggiornato)\s*:?\s*"
    r"(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{4}"  # DD/MM/YYYY or similar
    r"|\d{4}[/\-\.]\d{1,2}[/\-\.]\d{1,2}"  # YYYY-MM-DD
    r"|\w+\s+\d{1,2},?\s+\d{4})",  # Month DD, YYYY
    re.IGNORECASE,
)


def _parse_date_flexible(date_str: str) -> datetime | None:
    """Try to parse a date string in common formats. Returns None on failure."""
    if not date_str:
        return None
    # Prendi solo i primi 10 char per formato ISO
    clean = str(date_str).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%d.%m.%Y"):
        try:
            return datetime.strptime(clean[:10], fmt).replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            continue
    # Prova formato "Month DD, YYYY"
    try:
        # Rimuovi virgola e prova
        clean_no_comma = clean.replace(",", "")
        return datetime.strptime(clean_no_comma[:20].strip(), "%B %d %Y").replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        pass
    return None


def detect_temporal_coherence(soup, clean_text: str | None = None) -> MethodScore:
    """Detect temporal signal coherence across schema dates and visible content dates.

    Compares dateModified/datePublished from JSON-LD schema with visible
    'Last updated' / 'Updated' patterns in text. Coherent dates (< 30 days
    apart) get full score; incoherent dates (> 90 days) get a warning.
    """
    body_text = clean_text or _get_clean_text(soup)
    dates_found: dict[str, datetime] = {}

    # 1. Schema JSON-LD: dateModified, datePublished
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
            items = data if isinstance(data, list) else [data]
            for item in items:
                if not isinstance(item, dict):
                    continue
                for key in ("dateModified", "datePublished"):
                    if key in item:
                        parsed = _parse_date_flexible(str(item[key]))
                        if parsed:
                            dates_found[f"schema_{key}"] = parsed
        except (json.JSONDecodeError, TypeError):
            continue

    # 2. Meta tag article:modified_time / article:published_time
    for meta_prop, label in [
        ("article:modified_time", "meta_modified"),
        ("article:published_time", "meta_published"),
    ]:
        meta = soup.find("meta", attrs={"property": meta_prop})
        if meta and meta.get("content"):
            parsed = _parse_date_flexible(meta["content"])
            if parsed:
                dates_found[label] = parsed

    # 3. Pattern visibile nel testo: "Last updated: DATE", "Updated: DATE"
    matches = _UPDATED_DATE_RE.findall(body_text)
    for i, match in enumerate(matches[:3]):  # Max 3 match
        parsed = _parse_date_flexible(match)
        if parsed:
            dates_found[f"visible_updated_{i}"] = parsed

    # 4. Calcola coerenza
    date_values = list(dates_found.values())
    is_coherent = False
    is_incoherent = False
    max_diff_days = 0

    if len(date_values) >= 2:
        # Calcola differenza massima tra tutte le coppie
        for i in range(len(date_values)):
            for j in range(i + 1, len(date_values)):
                diff = abs((date_values[i] - date_values[j]).days)
                max_diff_days = max(max_diff_days, diff)

        if max_diff_days <= 30:
            is_coherent = True
        elif max_diff_days > 90:
            is_incoherent = True

    # Score
    score = 0
    if len(date_values) >= 2 and is_coherent:
        score = 4  # Punteggio pieno: date presenti e coerenti
    elif len(date_values) >= 2 and not is_incoherent:
        score = 2  # Date presenti, differenza moderata (30-90 giorni)
    elif len(date_values) == 1:
        score = 1  # Solo una data trovata
    # Se incoerenti (> 90 giorni) o nessuna data: score = 0

    return MethodScore(
        name="temporal_coherence",
        label="Temporal Signal Coherence",
        detected=len(date_values) >= 2 and is_coherent,
        score=min(score, 4),
        max_score=4,
        impact="+8%",
        details={
            "dates_found": {k: v.isoformat() for k, v in dates_found.items()},
            "date_count": len(date_values),
            "max_diff_days": max_diff_days,
            "is_coherent": is_coherent,
            "is_incoherent": is_incoherent,
        },
    )


# ─── Internal Link Anchor Text (+5%) — Batch B v3.16.0 ──────────────────────

# Anchor text generici da penalizzare
_GENERIC_ANCHORS = {
    "click here",
    "read more",
    "learn more",
    "here",
    "this",
    "link",
    "more",
    "continue",
    "go",
    "see more",
    "clicca qui",
    "leggi di più",
    "scopri di più",
    "qui",
    "questo",
}


def detect_anchor_text_quality(soup, base_url: str) -> MethodScore:
    """Detect internal link anchor text quality.

    Counts internal links with generic anchor text ('click here', 'read more',
    'here', etc.) vs descriptive anchor text (> 3 words, not generic).
    Score: > 80% descriptive = full, < 50% = 0.
    """
    parsed_base = urlparse(base_url)
    base_domain = parsed_base.netloc.replace("www.", "")

    generic_count = 0
    descriptive_count = 0
    total_internal = 0

    for a in soup.find_all("a", href=True):
        href = a["href"]
        # Determina se è un link interno
        if href.startswith("http"):
            link_domain = urlparse(href).netloc.replace("www.", "")
            if link_domain != base_domain:
                continue  # Link esterno, skip
        elif href.startswith("#") or href.startswith("mailto:") or href.startswith("tel:"):
            continue  # Ancora interna o mailto/tel, skip

        # È un link interno
        anchor_text = a.get_text(strip=True).lower()
        if not anchor_text:
            continue

        total_internal += 1

        # Controlla se è generico
        if anchor_text in _GENERIC_ANCHORS:
            generic_count += 1
        elif len(anchor_text.split()) > 3:
            descriptive_count += 1
        else:
            # Anchor corto (1-3 parole) ma non generico — conta come parziale
            descriptive_count += 1

    if total_internal == 0:
        # Nessun link interno: score neutro
        return MethodScore(
            name="anchor_text_quality",
            label="Anchor Text Quality",
            detected=False,
            score=2,
            max_score=3,
            impact="+5%",
            details={
                "total_internal_links": 0,
                "generic_count": 0,
                "descriptive_count": 0,
                "descriptive_ratio": 0,
            },
        )

    descriptive_ratio = descriptive_count / total_internal

    if descriptive_ratio >= 0.8:
        score = 3
    elif descriptive_ratio >= 0.5:
        score = 2
    elif descriptive_ratio > 0:
        score = 1
    else:
        score = 0

    return MethodScore(
        name="anchor_text_quality",
        label="Anchor Text Quality",
        detected=descriptive_ratio >= 0.8,
        score=min(score, 3),
        max_score=3,
        impact="+5%",
        details={
            "total_internal_links": total_internal,
            "generic_count": generic_count,
            "descriptive_count": descriptive_count,
            "descriptive_ratio": round(descriptive_ratio, 2),
        },
    )


# ─── International GEO (+5%) — Batch B v3.16.0 ─────────────────────────────


def detect_international_geo(soup) -> MethodScore:
    """Detect international GEO signals: hreflang tags, html lang, schema inLanguage.

    Only scores if the site HAS hreflang tags — does not penalize monolingual sites.
    """
    score = 0

    # 1. <html lang="...">
    html_tag = soup.find("html")
    html_lang = html_tag.get("lang", "").strip() if html_tag else ""

    # 2. <link rel="alternate" hreflang="..."> tags
    hreflang_tags = soup.find_all("link", attrs={"rel": "alternate", "hreflang": True})
    hreflang_langs = [tag.get("hreflang", "") for tag in hreflang_tags if tag.get("hreflang")]

    # 3. Schema inLanguage
    in_language = None
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
            items = data if isinstance(data, list) else [data]
            for item in items:
                if isinstance(item, dict) and "inLanguage" in item:
                    in_language = item["inLanguage"]
                    break
        except (json.JSONDecodeError, TypeError):
            continue
        if in_language:
            break

    # Solo se il sito ha hreflang, assegna punteggio
    has_hreflang = len(hreflang_langs) > 0

    if not has_hreflang:
        # Sito monolingua: score neutro (0), non penalizzare
        return MethodScore(
            name="international_geo",
            label="International GEO",
            detected=False,
            score=0,
            max_score=3,
            impact="+5%",
            details={
                "html_lang": html_lang,
                "hreflang_count": 0,
                "hreflang_langs": [],
                "schema_inLanguage": in_language,
                "is_multilingual": False,
            },
        )

    # Ha hreflang: assegna punteggio
    if len(hreflang_langs) >= 3:
        score += 2
    elif len(hreflang_langs) >= 1:
        score += 1

    if in_language:
        score += 1

    return MethodScore(
        name="international_geo",
        label="International GEO",
        detected=True,
        score=min(score, 3),
        max_score=3,
        impact="+5%",
        details={
            "html_lang": html_lang,
            "hreflang_count": len(hreflang_langs),
            "hreflang_langs": hreflang_langs,
            "schema_inLanguage": in_language,
            "is_multilingual": True,
        },
    )


# ─── AI Crawl Budget (+5%) — Batch B v3.16.0 ────────────────────────────────


def detect_crawl_budget(soup) -> MethodScore:
    """Detect AI crawl budget signals from HTML meta tags and head links.

    Since citability analysis only has access to HTML (not robots.txt),
    checks: link rel='sitemap' in head, meta robots noindex/nofollow penalties.
    """
    score = 3  # Punteggio pieno di default, con penalità
    penalties = []

    # 1. Controlla meta robots per noindex/nofollow
    meta_robots = soup.find("meta", attrs={"name": re.compile(r"^robots$", re.I)})
    has_noindex = False
    has_nofollow = False
    if meta_robots:
        content = (meta_robots.get("content") or "").lower()
        if "noindex" in content:
            has_noindex = True
            penalties.append("meta robots noindex")
            score -= 2
        if "nofollow" in content:
            has_nofollow = True
            penalties.append("meta robots nofollow")
            score -= 1

    # 2. Controlla X-Robots-Tag meta (alternativa)
    meta_x_robots = soup.find("meta", attrs={"http-equiv": re.compile(r"x-robots-tag", re.I)})
    if meta_x_robots:
        content = (meta_x_robots.get("content") or "").lower()
        if "noindex" in content and not has_noindex:
            has_noindex = True
            penalties.append("X-Robots-Tag noindex")
            score -= 2
        if "nofollow" in content and not has_nofollow:
            has_nofollow = True
            penalties.append("X-Robots-Tag nofollow")
            score -= 1

    # 3. Cerca link rel="sitemap" nel <head>
    has_sitemap_link = False
    sitemap_link = soup.find("link", attrs={"rel": "sitemap"})
    if sitemap_link and sitemap_link.get("href"):
        has_sitemap_link = True

    # Bonus se sitemap è referenziata nel head (segnale positivo per AI crawler)
    if not has_sitemap_link and score > 0:
        # Non penalizzare, ma niente bonus
        pass

    score = max(score, 0)

    return MethodScore(
        name="crawl_budget",
        label="AI Crawl Budget",
        detected=not has_noindex and not has_nofollow,
        score=min(score, 3),
        max_score=3,
        impact="+5%",
        details={
            "has_noindex": has_noindex,
            "has_nofollow": has_nofollow,
            "has_sitemap_link": has_sitemap_link,
            "penalties": penalties,
        },
    )


# ─── Orchestrator ─────────────────────────────────────────────────────────────

# Suggerimenti di miglioramento per ogni metodo non rilevato
_IMPROVEMENT_SUGGESTIONS = {
    "quotation_addition": "Add attributed quotes in <blockquote> (+41% AI visibility)",
    "statistics_addition": "Include quantitative data: percentages, figures, metrics (+33%)",
    "fluency_optimization": "Improve fluency with longer paragraphs and logical connectives (+29%)",
    "cite_sources": "Cite authoritative sources (.edu, .gov, Wikipedia) with external links (+27%)",
    "answer_first": "Start each section with a concrete fact in the first sentence (+25% AI citation)",
    "passage_density": "Write self-contained paragraphs of 50-150 words with numeric data (+23%)",
    "technical_terms": "Use domain-specific technical terminology (+18%)",
    "authoritative_tone": "Add author bio with credentials and assertive tone (+16%)",
    "readability": "Target Flesch-Kincaid Grade 6-8 with 100-150 word sections (+15% AI citation)",
    "citability_density": "Add 2+ citable facts (numbers, names, dates) per paragraph (+15%)",
    "easy_to_understand": "Improve readability: short sentences, hierarchical headings, FAQ (+14%)",
    "faq_in_content": "Add FAQ patterns in content: headings ending with '?' followed by answers (+12%)",
    "content_freshness": "Add dateModified in JSON-LD and reference current year in content (+10%)",
    "definition_patterns": "Start sections with definitions: 'X is...', 'X refers to...' (+10%)",
    "image_alt_quality": "Write descriptive alt text (>10 chars, not generic) for all images (+8%)",
    "format_mix": "Mix content formats: paragraphs + bullet lists + tables (+8%)",
    "unique_words": "Vary vocabulary: use synonyms, avoid repetitions (+7%)",
    "keyword_stuffing": "Reduce density of repeated keywords (-9% if present)",
    # Quality Signals Batch 2
    "attribution_completeness": "Add inline attributions: 'according to X', 'Y (2024) found that' (+12%)",
    "no_negative_signals": "Remove excessive CTAs, add author info, avoid repetitive phrases (-15%)",
    "comparison_content": "Add comparison tables, pro/con sections, or 'X vs Y' headings (+10%)",
    "eeat_signals": "Add privacy policy, terms, about page, and contact links for E-E-A-T trust (+15%)",
    "no_content_decay": "Update old year references and add recent dateModified (-10%)",
    "boilerplate_ratio": "Ensure main content is >60% of page text; use <main> or <article> tags (+8%)",
    "nuance_signals": "Add nuance: 'however', 'limitations include', 'on the other hand' (+5%)",
    # Quality Signals Batch 3+4
    "snippet_ready": "Add snippet-ready definitions after headings: 'X is...', 'X refers to...' (+10%)",
    "chunk_quotability": "Write self-contained paragraphs (50-150 words) with concrete data for AI quoting (+10%)",
    "blog_structure": "Add Article/BlogPosting schema with datePublished, author, and categories (+8%)",
    "shopping_readiness": "Add Product schema with price, availability, and AggregateRating (+8%)",
    "chatgpt_shopping": "Complete Product schema with name, price, image, availability, brand for ChatGPT Shopping (+8%)",
    # Quality Signals Batch A v3.16.0
    "voice_search_ready": "Add question-format headings with concise answers for voice search (+5%)",
    "multi_platform": "Add 3+ platform links in sameAs schema (GitHub, LinkedIn, Twitter, etc.) (+10%)",
    "entity_disambiguation": "Use consistent naming across title, og:title, and schema; add explicit definition (+8%)",
    "first_party_data": "Include original research signals: 'our data shows', methodology section (+12%)",
    "no_stale_data": "Remove stale year references and update copyright year (-10%)",
    "social_proof": "Add testimonials, AggregateRating with reviews, or trust badges (+8%)",
    "accessibility_signals": "Use semantic HTML (<main>, <nav>), ARIA landmarks, and skip links (+5%)",
    "conversion_funnel": "Add visible CTAs, pricing page link, and contact information (+8%)",
    # Quality Signals Batch B v3.16.0
    "temporal_coherence": "Add coherent date signals: schema dateModified, visible 'Last updated' dates within 30 days (+8%)",
    "anchor_text_quality": "Use descriptive anchor text for internal links instead of 'click here' or 'read more' (+5%)",
    "international_geo": "Add hreflang tags and schema inLanguage for multilingual sites (+5%)",
    "crawl_budget": "Remove meta robots noindex/nofollow to allow AI crawlers to index content (+5%)",
}

# Ordine per impatto decrescente (escluso penalità)
_METHOD_ORDER = [
    "quotation_addition",
    "statistics_addition",
    "fluency_optimization",
    "cite_sources",
    "answer_first",
    "passage_density",
    "technical_terms",
    "authoritative_tone",
    "eeat_signals",
    "readability",
    "citability_density",
    "easy_to_understand",
    "attribution_completeness",
    "faq_in_content",
    "content_freshness",
    "comparison_content",
    "definition_patterns",
    "image_alt_quality",
    "boilerplate_ratio",
    "format_mix",
    "unique_words",
    "nuance_signals",
    "snippet_ready",
    "chunk_quotability",
    "blog_structure",
    "shopping_readiness",
    "chatgpt_shopping",
    # Quality Signals Batch A v3.16.0
    "first_party_data",
    "multi_platform",
    "entity_disambiguation",
    "social_proof",
    "conversion_funnel",
    "voice_search_ready",
    "accessibility_signals",
    # Quality Signals Batch B v3.16.0
    "temporal_coherence",
    "anchor_text_quality",
    "international_geo",
    "crawl_budget",
    # Penalità
    "keyword_stuffing",
    "no_negative_signals",
    "no_content_decay",
    "no_stale_data",
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


def audit_citability(soup, base_url: str, soup_clean=None) -> CitabilityResult:
    """Analyze content citability with 42 methods (Princeton GEO + AutoGEO + content analysis).

    Args:
        soup: BeautifulSoup of the HTML page.
        base_url: Base URL of the site.
        soup_clean: (opzionale) soup pre-pulito da script/style (fix #285).

    Returns:
        CitabilityResult with score 0-100 and per-method detail.
    """
    # Fix #285: passa soup_clean a _get_clean_text per evitare re-parse
    clean_text = _get_clean_text(soup, soup_clean=soup_clean)

    methods = [
        # Metodi Princeton GEO originali (ricalibrati)
        detect_quotations(soup, clean_text=clean_text),
        detect_statistics(soup, clean_text=clean_text),
        detect_fluency(soup, clean_text=clean_text),
        detect_cite_sources(soup, base_url),
        detect_answer_first(soup),
        detect_passage_density(soup),
        detect_technical_terms(soup, clean_text=clean_text),
        detect_authoritative_tone(soup, clean_text=clean_text),
        detect_easy_to_understand(soup),
        detect_unique_words(soup, clean_text=clean_text),
        detect_keyword_stuffing(soup, clean_text=clean_text),
        # Nuovi metodi content analysis v3.15
        detect_readability(soup, clean_text=clean_text),
        detect_faq_in_content(soup),
        detect_image_alt_quality(soup),
        detect_content_freshness(soup, clean_text=clean_text),
        detect_citability_density(soup, clean_text=clean_text),
        detect_definition_patterns(soup),
        detect_format_mix(soup),
        # Quality Signals Batch 2 (bonus — cappati a 100 dal totale)
        detect_attribution(soup, clean_text=clean_text),
        detect_negative_signals(soup, clean_text=clean_text),
        detect_comparison_content(soup, clean_text=clean_text),
        detect_eeat(soup),
        detect_content_decay(soup, clean_text=clean_text),
        detect_boilerplate_ratio(soup),
        detect_nuance_signals(soup, clean_text=clean_text),
        # Quality Signals Batch 3+4 (bonus — cappati a 100 dal totale)
        detect_snippet_ready(soup),
        detect_chunk_quotability(soup),
        detect_blog_structure(soup),
        detect_shopping_readiness(soup),
        detect_chatgpt_shopping(soup),
        # Quality Signals Batch A v3.16.0 (bonus — cappati a 100 dal totale)
        detect_voice_search(soup),
        detect_multi_platform(soup),
        detect_entity_disambiguation(soup),
        detect_first_party_data(soup, clean_text=clean_text),
        detect_stale_data(soup, clean_text=clean_text),
        detect_social_proof(soup, clean_text=clean_text),
        detect_accessibility_signals(soup),
        detect_conversion_funnel(soup),
        # Quality Signals Batch B v3.16.0
        detect_temporal_coherence(soup, clean_text=clean_text),
        detect_anchor_text_quality(soup, base_url),
        detect_international_geo(soup),
        detect_crawl_budget(soup),
    ]

    # Somma score (max possibile = 100)
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
