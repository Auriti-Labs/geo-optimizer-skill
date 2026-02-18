# Princeton GEO Methods — The 9 Official Methods

> Source: "GEO: Generative Engine Optimization" — Aggarwal et al., KDD 2024  
> Paper: https://arxiv.org/abs/2311.09735  
> Dataset/Code: https://generative-engines.com/GEO/  
> Tested on: Perplexity.ai (real), GPT-4 (simulated), 10,000 diverse queries

## Overview

Princeton research identified and tested **9 GEO methods** on GEO-bench (10,000 queries from diverse domains: science, history, law, finance, health...).

**Key result:** The best methods increase AI visibility by up to **+40%** (with peaks up to **+115%** for specific ranking positions).

Visibility is measured through proprietary metrics for generative engines:
- **Word Count**: how many words from your content appear in the AI response
- **Rank Position**: where your source is cited
- **Citation Count**: how many times you are cited

---

## Method 1 — Cite Sources

**Estimated impact: +30–115% for AI visibility**

### Description
Adding links and references to authoritative external sources directly in the page text. This is the method with the **most variable** but potentially highest impact: +115% for rank-5 position.

### How to implement it
1. Identify every claim in your content
2. Find and link the primary source (paper, study, official site)
3. Use the format: `According to [Source](URL), ...`
4. Prefer linking to: academic papers, government sites (.gov, .edu), industry reports

### Practical example
**Before:** "Fixed-rate mortgages are safer during periods of inflation."  
**After:** "According to the [Federal Reserve](https://federalreserve.gov), fixed-rate mortgages better protect borrowers during inflationary periods exceeding 3%."

### Notes
- Particularly effective for informational and transactional queries
- AI engines use the presence of citations as a trust signal
- Variable effect: can be negative for rank-1 but very positive for rank-3+

---

## Method 2 — Statistics

**Estimated impact: +40% average visibility**

### Description
Including specific quantitative data, percentages, concrete numbers, and measurable metrics in content. AI engines tend to prefer content with verifiable facts.

### How to implement it
1. Replace generic statements with specific numerical data
2. Include: percentages, monetary values, dates, sizes, study results
3. Always specify the source and year of the data
4. Use comparative numerical contexts ("compared to 2023, +15%")

### Practical example
**Before:** "Many Americans invest in mutual funds."  
**After:** "34.2% of Americans hold mutual fund shares (Morningstar, 2024), with total assets under management exceeding $23 trillion."

### Notes
- Works best combined with Cite Sources
- Specific numbers increase the likelihood of being extracted and cited
- Avoid statistics that are too old (>3 years) or imprecise

---

## Method 3 — Quotation Addition

**Estimated impact: +30–40% visibility**

### Description
Including quoted text from experts, authorities, or official documents. Quotation marks signal to AI that the content is attributed and verifiable.

### How to implement it
1. Find quotes from relevant experts (CEOs, researchers, regulators)
2. Use the format: `"Quote text" — Expert Name, Role, Year`
3. Include at least 1-2 quotes per page
4. Also cite official documents: laws, regulations, standards

### Practical example
```
"A fixed rate is the right choice when market rates 
are below the historical average" — John Smith, Head of 
Mortgage Lending, Bloomberg 2024
```

### Notes
- Very effective for Finance, Health, Legal domains (YMYL)
- AI engines prefer content with clear attribution
- Alternate short quotes with context explanations

---

## Method 4 — Authoritative

**Estimated impact: +6–12% average visibility**

### Description
Rewriting content with an expert sectoral tone instead of a generic one. Includes: use of precise terminology, logical structure, absence of vagueness.

### How to implement it
1. Eliminate vague phrases: "often", "generally", "might"
2. Use correct technical terminology for the sector
3. Structure with: definition → explanation → practical implications
4. Add professional context: "From a financial standpoint..."
5. Avoid commercial/promotional tone

### Practical example
**Before:** "A mortgage might be right for you if you need to buy a house."  
**After:** "A mortgage is a long-term financing instrument (15–30 years) secured by a lien on the property. The monthly payment includes principal and interest calculated on the agreed rate (fixed or variable)."

### Notes
- More consistent impact compared to other methods
- Particularly important for YMYL domains (finance, health, legal)
- Combine with Technical Terms for better results

---

## Method 5 — Fluency Optimization

**Estimated impact: +15–30% visibility**

### Description
Improving the flow and readability of text. Smooth, well-structured, and coherent text is preferred by LLM models for information extraction.

### How to implement it
1. Use medium-length sentences (15–25 words)
2. Vary sentence structure
3. Eliminate grammar errors and typos
4. Use logical connectives: "therefore", "however", "consequently", "in particular"
5. Structure paragraphs with: topic sentence → development → conclusion

### Useful tools
- Grammarly / LanguageTool for errors
- Hemingway App for readability
- Test with reading level score

### Practical example
**Before:** "The mortgage calculation, which is done by the bank, depends on the rate. The rate can be fixed or variable. You need to choose."  
**After:** "The mortgage payment calculation depends primarily on the type of rate chosen. A fixed rate guarantees stable payments throughout the loan term, while a variable rate may decrease or increase based on market benchmarks like SOFR or Euribor."

---

## Method 6 — Easy-to-Understand

**Estimated impact: +8–15% visibility**

### Description
Simplifying complex technical language without losing precision. AI engines prefer understandable text that can be easily extracted and paraphrased.

### How to implement it
1. After each technical term, add a brief explanation in parentheses
2. Use analogies for complex concepts
3. Create glossaries for industry terms
4. Structure with "What is it", "How it works", "When to use it"

### Practical example
**Before:** "The loan-to-value ratio influences the LTV of collateral guarantees."  
**After:** "The loan-to-value ratio (LTV) measures how much of the property price you are borrowing. An LTV of 80% means you are financing 80% of the value, with the remaining 20% as your down payment."

### Notes
- Do not sacrifice precision for simplicity
- Use a two-level structure: simple explanation + technical details

---

## Method 7 — Unique Words

**Estimated impact: +5–8% visibility**

### Description
Enriching vocabulary by avoiding excessive repetition. A varied vocabulary signals content quality.

### How to implement it
1. Identify repeated words using tools like WordCounter
2. Use contextually appropriate synonyms
3. Alternate between technical and common terms for the same concept
4. Use a sector-specific thesaurus

### Note
**Lower** impact compared to other methods. Do not prioritize.

---

## Method 8 — Technical Terms

**Estimated impact: +5–10% for specialized queries**

### Description
Using sector-specific technical terminology appropriately. Increases relevance for specialized queries from expert users.

### How to implement it
1. Include official acronyms (APR, LTV, ROI, EBITDA)
2. Use industry-standard terms in their correct form
3. Do not overdo it: balance technical terms with Easy-to-Understand

### Example
"APR (Annual Percentage Rate)", "SOFR 3M", "credit spread", "French amortization"

### Note
Works **in combination** with Authoritative and Cite Sources.

---

## Method 9 — Keyword Stuffing ⚠️

**Estimated impact: Neutral or NEGATIVE**

### Description
Forcefully inserting keywords into text at high density. Princeton research demonstrated it is **not effective** for GEO and can be counterproductive.

### Research result
- No significant improvement in AI visibility
- Can worsen Fluency (net negative impact)
- Residual technique from traditional SEO — **do not apply for GEO**

### What to do instead
Use Fluency Optimization + Cite Sources + Statistics for real results.

---

## Impact Summary by Domain

| Method | Science | Finance | Health | History | Media |
|--------|---------|---------|--------|---------|-------|
| Cite Sources | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐ |
| Statistics | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐ |
| Quotation | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐ |
| Authoritative | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐ |
| Fluency | ⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐ |
| Easy-Understand | ⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐ | ⭐⭐⭐ |

---

## Recommended Implementation Strategy

### Phase 1 — Quick Wins (week 1–2)
1. **Statistics**: add numerical data to main pages (+40%)
2. **Cite Sources**: add 2–3 links to authoritative sources per page (+30%)
3. **Fluency**: revise text for readability

### Phase 2 — Optimization (week 3–4)
4. **Quotation Addition**: add expert quotes
5. **Authoritative**: reorganize content with expert structure
6. **Technical Terms**: verify correct terminology

### Phase 3 — Fine Tuning
7. **Easy-to-Understand**: add glossaries and explanations
8. **Unique Words**: revise repetitions

> ⚠️ **Do not do**: Keyword Stuffing (method 9) — counterproductive for GEO

---

## References

- Original paper: https://arxiv.org/abs/2311.09735
- Princeton Collaborate: https://collaborate.princeton.edu/en/publications/geo-generative-engine-optimization/
- GEO-bench dataset: https://generative-engines.com/GEO/
- KDD 2024 Conference: August 25–29, 2024, Barcelona
