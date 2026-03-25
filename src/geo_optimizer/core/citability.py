"""
Citability Score — Content analysis with 18 methods (Princeton GEO + content analysis).

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


def detect_fluency(soup) -> MethodScore:
    """Estimate text fluency through structural heuristics."""
    paragraphs = soup.find_all("p")
    if not paragraphs:
        return MethodScore(name="fluency_optimization", label="Fluency Optimization", max_score=6, impact="+29%")

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


def detect_content_freshness(soup) -> MethodScore:
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
    body_text = _get_clean_text(soup)
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
}

# Ordine per impatto decrescente (escluso keyword_stuffing che è una penalità)
_METHOD_ORDER = [
    "quotation_addition",
    "statistics_addition",
    "fluency_optimization",
    "cite_sources",
    "answer_first",
    "passage_density",
    "technical_terms",
    "authoritative_tone",
    "readability",
    "citability_density",
    "easy_to_understand",
    "faq_in_content",
    "content_freshness",
    "definition_patterns",
    "image_alt_quality",
    "format_mix",
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


def audit_citability(soup, base_url: str, soup_clean=None) -> CitabilityResult:
    """Analyze content citability with 18 methods (Princeton GEO + content analysis).

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
        detect_quotations(soup),
        detect_statistics(soup, clean_text=clean_text),
        detect_fluency(soup),
        detect_cite_sources(soup, base_url),
        detect_answer_first(soup),
        detect_passage_density(soup),
        detect_technical_terms(soup, clean_text=clean_text),
        detect_authoritative_tone(soup),
        detect_easy_to_understand(soup),
        detect_unique_words(soup, clean_text=clean_text),
        detect_keyword_stuffing(soup, clean_text=clean_text),
        # Nuovi metodi content analysis v3.15
        detect_readability(soup, clean_text=clean_text),
        detect_faq_in_content(soup),
        detect_image_alt_quality(soup),
        detect_content_freshness(soup),
        detect_citability_density(soup, clean_text=clean_text),
        detect_definition_patterns(soup),
        detect_format_mix(soup),
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
