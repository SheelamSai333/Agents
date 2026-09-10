# SEO Intelligence & Verification Agent System

A production-grade, multi-capability SEO intelligence and factual consistency platform built with Python. The system analyzes public websites using deterministic, evidence-backed techniques across three core engines:

1. **Q1 — On-Page SEO Auditor**: Deep technical SEO inspection evaluating structural markup, metadata, content quality, and HTTP status codes against 13 deterministic audit rules with evidence citations.
2. **Q2 — NAP Consistency Checker**: Local business Name, Address, and Phone number (NAP) consistency evaluator that extracts data from JSON-LD, Microdata, and HTML fallbacks, normalizes values across international formats, and detects genuine business discrepancies across pages.
3. **Q3 — Grounded Website Question Answering**: Evidence-grounded natural-language question-answering agent that crawls website pages, retrieves relevant passages, extracts verbatim excerpts from source text without hallucination or paraphrasing, and deterministically returns `null` when a query is unsupported.

---

## Table of Contents

- [1. Features](#1-features)
  - [Q1 — On-Page SEO Auditor](#q1--on-page-seo-auditor)
  - [Q2 — NAP Consistency Checker](#q2--nap-consistency-checker)
  - [Q3 — Grounded Website Question Answering](#q3--grounded-website-question-answering)
- [2. Architecture](#2-architecture)
- [3. Repository Structure](#3-repository-structure)
- [4. Requirements & Prerequisites](#4-requirements--prerequisites)
- [5. Installation](#5-installation)
- [6. How to Run Q1 (SEO Audit)](#6-how-to-run-q1-seo-audit)
- [7. How to Run Q2 (NAP Consistency Checker)](#7-how-to-run-q2-nap-consistency-checker)
- [8. How to Run Q3 (Grounded Question Answering)](#8-how-to-run-q3-grounded-question-answering)
- [9. Output Files](#9-output-files)
- [10. How to Test the Project](#10-how-to-test-the-project)
- [11. Example Testing Workflow](#11-example-testing-workflow)
- [12. Q3 Grounding & Anti-Hallucination Mechanism](#12-q3-grounding--anti-hallucination-mechanism)
- [13. Q2 Evidence & Confidence Model](#13-q2-evidence--confidence-model)
- [14. Design Principles](#14-design-principles)
- [15. Limitations & Operational Considerations](#15-limitations--operational-considerations)
- [16. Troubleshooting](#16-troubleshooting)
- [17. GitHub Usage](#17-github-usage)
- [18. Submission & Demo Guidelines](#18-submission--demo-guidelines)
- [19. Security & Privacy](#19-security--privacy)

---

## 1. Features

### Q1 — On-Page SEO Auditor
- **Autonomous BFS Crawler**: Crawls internal site links within defined page and depth boundaries, respecting `robots.txt` directives, loop prevention rules, and politeness delays.
- **Hybrid SPA Rendering**: Automatically detects JavaScript Single Page Applications (SPAs) with empty shells and falls back to headless Chromium rendering via Playwright.
- **13 Deterministic SEO Rules**: Evaluates HTTP status codes, title tags, meta descriptions, robots directives, heading hierarchy ($H_1 \to H_6$), image alt text, canonical links, internal/external link integrity, mixed-content HTTPS security, social metadata (Open Graph / Twitter Cards), thin content, and HTML language declarations.
- **Concrete Evidence Citations**: Every finding includes the offending URL, exact DOM tag excerpt, character/word count, and suggested remediation.
- **Severity Scoring**: Findings are categorized into `critical`, `high`, `medium`, `low`, and `info` with weighted score impacts.
- **Dual JSON Reporting**: Generates both an itemized finding list (`audit.json`) and an aggregated executive summary (`audit_summary.json`), complemented by a terminal overview table.

### Q2 — NAP Consistency Checker
- **Page Discovery & Prioritization**: Automatically prioritizes high-value business identity pages (homepage, `/contact`, `/about`, location/store directories, headers, and footers).
- **Multi-Source Structured Data Extraction**: Parses Schema.org `LocalBusiness` and `Organization` entities from JSON-LD blocks (including `@graph` trees, root arrays, and nested `PostalAddress` nodes) as well as HTML5 Microdata (`itemscope`, `itemprop`).
- **Semantic HTML Fallback Extraction**: Extracts `tel:` links, `<address>` tags, title brand snippets, and footer text patterns.
- **Cross-Jurisdiction Normalization**:
  - **Phone**: Normalizes E.164 international numbers, Indian local/country-code formats, US standard formatting, and UK phone structures.
  - **Address**: Expands standard road abbreviations (`st.` $\to$ `street`, `rd.` $\to$ `road`, `ave.` $\to$ `avenue`, `blvd.` $\to$ `boulevard`, etc.), strips redundant punctuation, and segments addresses into comparable components (`street`, `city`, `state`, `postal_code`).
  - **Name**: Normalizes corporate legal suffixes (`LLC`, `Inc`, `Ltd`, `Corp`) and isolates brand tokens from composite `<title>` tags.
- **Deterministic Comparison Engine**: Distinguishes between harmless formatting variations and genuine business discrepancies. Emits one of five standardized verdicts:
  - `consistent`: All discovered values represent the same canonical identity.
  - `minor_formatting_difference`: Values differ only in cosmetic formatting or abbreviation expansions.
  - `genuine_mismatch`: Conflicting business identities, phone numbers, or address components detected.
  - `uncertain`: Extraction relies on low-confidence heuristics (e.g. logo alt text) without corroboration.
  - `not_found`: The field was not found on any analyzed page.
- **Source-Quality Weighted Confidence**: Calculates confidence scores based on source authority (`json_ld` 1.0 > `microdata` 0.9 > `tel_link` 0.85 > `html_text` 0.5 > `logo_alt` 0.3).
- **Array JSON Output**: Writes findings to `nap_report.json` as a JSON array of field reports.

### Q3 — Grounded Website Question Answering
- **Zero-Hallucination Retrieval**: Accepts a natural-language query and crawls discoverable website content to locate the specific page answering the question.
- **Verbatim Excerpt Extraction**: Extracts contiguous, unaltered passages directly from the rendered DOM text. Never paraphrases, summarizes, re-orders, or generates text.
- **Semantic Intent & Predicate Matching**: Classifies query intent (`DEFINITION`, `LOCATION`, `PRICE_COST`, `PROCEDURAL`, `GENERAL`) and requires explanatory predicates (`X is...`, `X helps...`, `X provides...`, `X allows...`, `X enables...`, `X serves as...`, `X refers to...`) for definition questions, suppressing incidental instrumental mentions (`...in X`, `...using X`).
- **Start-URL Proximity Boost**: Prioritizes the user-supplied target URL (`depth = 0`) while still allowing another page to win if it contains substantially stronger evidence.
- **Deterministic Null Fallback**: If the answer is not supported by the crawled content, or if only incidental mentions exist without an explanatory predicate, it strictly outputs `null` for both the URL and excerpt.
- **Grounding Verification**: Before emitting output, verifies that the excerpt is an exact contiguous substring of the source page's visible text.
- **Standardized Output**: Emits results to `answer.json`.

---

## 2. Architecture

```
User CLI Input
     |
     v
  main.py (Unified CLI Entrypoint)
     |
     +---> --url <URL> (Default: Q1 SEO Audit)
     |        |
     |        v
     |     Crawler (BFS Queue + Playwright Headless Chromium Fallback)
     |        |
     |        v
     |     ParsedPage Models (DOM, Metadata, Headings, Links, Text)
     |        |
     |        v
     |     RuleEngine (13 Deterministic SEO Rules)
     |        |
     |        v
     |     JSONReporter -> audit.json & audit_summary.json
     |
     +---> --url <URL> --nap (Q2 NAP Consistency Checker)
     |        |
     |        v
     |     Crawler (BFS Crawl & Page Priority Queue)
     |        |
     |        v
     |     Extraction Pipeline (JSON-LD @graph/arrays, Microdata, HTML tags)
     |        |
     |        v
     |     Normalizers (Phone E.164, Address abbreviations/components, Name suffixes)
     |        |
     |        v
     |     ComparisonEngine & ConfidenceScorer
     |        |
     |        v
     |     NAPReporter -> nap_report.json
     |
     +---> --url <URL> --query <QUERY> (Q3 Grounded Website Q&A)
              |
              v
           Crawler (BFS Crawl of Discoverable Site Pages)
              |
              v
           ContentExtractor (Semantic DOM blocks, Breadcrumbs, Boilerplate Tagging)
              |
              v
           In-Memory Okapi BM25 Indexer (Passage-tuned b=0.40, Suffix Stemming)
              |
              v
           PassageSearcher (Intent Filtering, Predicate Detection, Depth Boost)
              |
              v
           ExcerptExtractor (Exact Contiguous Sentence Windowing)
              |
              v
           GroundingVerifier (Asserts excerpt in source page visible text)
              |
              v
           QAReporter -> answer.json
```

---

## 3. Repository Structure

```
agents/
│
├── main.py                         # Unified CLI entrypoint routing Q1, Q2, and Q3 workflows
├── requirements.txt                # Production and test Python dependencies
├── README.md                       # Comprehensive documentation
├── .gitignore                      # Git exclusion rules (cache, venv, temporary files)
│
├── seo_audit/                      # Q1: On-Page SEO Auditor Package
│   ├── __init__.py                 # Package exports
│   ├── config.py                   # AuditConfig dataclass (limits, politeness, timeouts)
│   ├── crawler.py                  # BFS crawler with queue, cycle detection, robots.txt compliance
│   ├── browser_renderer.py         # Headless Chromium renderer for JavaScript SPA hydration
│   ├── url_normalizer.py           # URL canonicalization, query parameter sorting, loop prevention
│   ├── robots.py                   # robots.txt parser and rule matcher
│   ├── parser.py                   # HTML DOM parser extracting metadata, headings, images, links
│   ├── models.py                   # Dataclasses: PageResponse, ParsedPage, SEOFinding, CrawlSummary
│   ├── engine.py                   # RuleEngine evaluating crawled pages against rule registry
│   ├── severity.py                 # Severity levels, issue deduplication, and score calculation
│   ├── evidence.py                 # Concrete evidence string formatters
│   ├── reporter.py                 # JSONReporter exporting audit.json, audit_summary.json, CLI table
│   └── rules/                      # 13 deterministic SEO audit rule implementations
│       ├── __init__.py             # Rule registry
│       ├── base.py                 # BaseRule abstract class
│       ├── http_status.py          # HTTP 4xx, 5xx, redirect chains
│       ├── title.py                # Title tag presence, length, duplicates
│       ├── meta_tags.py            # Meta descriptions presence, length, duplicates
│       ├── robots_meta.py          # noindex, nofollow, conflicting directives
│       ├── headings.py             # H1 presence, duplicates, skipped heading hierarchy
│       ├── images.py               # Missing or empty image alt attributes
│       ├── canonical.py            # Canonical link presence, validity, relative URLs
│       ├── links.py                # Internal broken links, empty hrefs, generic anchor text
│       ├── https_security.py       # Mixed-content insecure subresources on HTTPS pages
│       ├── social.py               # Missing Open Graph and Twitter Card tags
│       ├── content.py              # Thin content detection (<200 words)
│       └── language.py             # Missing or malformed html lang attributes
│
├── nap_checker/                    # Q2: NAP Consistency Checker Package
│   ├── __init__.py                 # Package exports
│   ├── checker.py                  # NAPChecker high-level orchestrator
│   ├── models.py                   # Dataclasses: NAPOccurrence, NAPEvidence, NAPFieldReport
│   ├── contact_detector.py         # Page prioritization heuristics (contact, about, locations)
│   ├── structured_data_extractor.py# JSON-LD (@graph, arrays, nested PostalAddress) & Microdata parser
│   ├── html_nap_extractor.py       # Heuristic extraction: tel links, address tags, title branding
│   ├── normalizers.py              # International phone, address abbreviation, and name normalization
│   ├── comparison_engine.py        # Deterministic comparison, address component analysis, verdicts
│   ├── confidence.py               # Source-weighted confidence scoring calculator
│   └── reporter.py                 # Exports nap_report.json array and formatted CLI summary table
│
├── site_qa/                        # Q3: Grounded Website Question-Answering Package
│   ├── __init__.py                 # Package exports
│   ├── agent.py                    # QAAgent end-to-end coordinator
│   ├── models.py                   # Dataclasses: ContentChunk, ScoredPassage, QAResponse
│   ├── content_extractor.py        # Semantic block parser, heading hierarchy, boilerplate filter
│   ├── query_processor.py          # Intent classifier, target subject isolation, stopword filter, stemming
│   ├── indexer.py                  # In-memory Okapi BM25 indexer with passage length tuning (b=0.40)
│   ├── searcher.py                 # PassageSearcher with predicate detection, depth boost, support gating
│   ├── excerpt_extractor.py        # Bounding sentence window extractor preserving exact verbatim text
│   ├── verifier.py                 # GroundingVerifier confirming substring existence in source visible text
│   └── reporter.py                 # Exports answer.json and formatted CLI summary table
│
├── tests/                          # Automated Pytest Test Suite (93 tests)
│   ├── __init__.py
│   ├── test_crawler.py             # Crawler page limits and depth boundaries (2 tests)
│   ├── test_parser.py              # DOM metadata extraction (1 test)
│   ├── test_reporter.py            # Q1 JSON output schema verification (1 test)
│   ├── test_rules_seo.py           # 13 SEO audit rules validation (12 tests)
│   ├── test_url_normalizer.py      # Normalization, loops, default ports, query params (10 tests)
│   ├── nap/                        # Q2 Test Suite (46 tests)
│   │   ├── __init__.py
│   │   ├── test_normalizers.py     # Phone, address abbreviations, legal suffixes (24 tests)
│   │   ├── test_extractors.py      # JSON-LD @graph, arrays, Microdata, logo alt quality (6 tests)
│   │   └── test_comparison_engine.py# Comparison engine verdicts and confidence (16 tests)
│   └── qa/                         # Q3 Test Suite (21 tests)
│       ├── __init__.py
│       ├── test_content_extractor.py # Block segmentation, boilerplate tagging (4 tests)
│       ├── test_indexer_searcher.py# BM25 ranking, phrase boost, boilerplate suppression (4 tests)
│       ├── test_intent_and_definitions.py# Intent classification, predicates, depth boost (5 tests)
│       ├── test_excerpt_extractor.py# Exact verbatim substring preservation (3 tests)
│       ├── test_unsupported_queries.py# Unsupported queries and null returns (3 tests)
│       └── test_qa_agent_e2e.py    # End-to-end multi-page routing and grounding verifier (2 tests)
│
├── audit.json                      # Generated Q1 finding items
├── audit_summary.json              # Generated Q1 audit executive summary
├── nap_report.json                 # Generated Q2 field consistency report
└── answer.json                     # Generated Q3 grounded QA response
```

---

## 4. Requirements & Prerequisites

### System Requirements
- **Python Version**: Python 3.10, 3.11, 3.12, or 3.13.
- **Operating System**: Windows (tested with PowerShell), macOS, or Linux.
- **Network**: Outbound HTTP/HTTPS access to target websites.

### Python Dependencies (from [requirements.txt](file:///c:/Users/sheel/Desktop/agents/requirements.txt))
- `httpx>=0.27.0`: High-performance HTTP client supporting HTTP/1.1, connection pooling, and SSL verification.
- `beautifulsoup4>=4.12.0`: HTML/XML DOM parsing and navigation.
- `lxml>=5.2.0`: Fast C-based HTML parsing engine.
- `pytest>=8.0.0`: Testing framework for running the 93 unit and integration tests.

### Optional Headless Browser (for JavaScript SPAs)
- `playwright`: If installed, enables automatic headless Chromium rendering for client-side JavaScript Single Page Applications (e.g. Next.js, React SPA). If Playwright is not installed, the crawler operates purely over standard HTTP responses.

---

## 5. Installation

### Step 1: Clone Repository
```powershell
git clone https://github.com/SheelamSai333/Agents.git
cd Agents
```
*(On Linux/macOS, use `cd Agents`).*

### Step 2: Create and Activate Virtual Environment
**On Windows PowerShell:**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**On Linux / macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Required Dependencies
```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4: Optional Headless Browser Setup (for SPAs)
If you wish to crawl client-rendered JavaScript SPAs:
```powershell
pip install playwright
playwright install chromium
```

### Step 5: Verify Installation
Run the test suite to ensure all 93 tests pass:
```powershell
python -m pytest tests/ -v
```

---

## 6. How to Run Q1 (SEO Audit)

The default execution mode of `main.py` runs the On-Page SEO Auditor.

### Basic Command
```powershell
python main.py --url "https://example.com"
```

### Advanced Crawl Options
```powershell
python main.py --url "https://example.com" --max-pages 50 --max-depth 4 --delay 0.2 --output "audit.json"
```

### Available CLI Arguments for Q1
| Argument | Type | Default | Description |
|---|---|---|---|
| `--url` | String | *Required* | Starting target website URL to audit. |
| `--max-pages` | Integer | `25` | Maximum number of internal pages to crawl. |
| `--max-depth` | Integer | `3` | Maximum link traversal depth from start URL. |
| `--timeout` | Float | `10.0` | HTTP request timeout in seconds. |
| `--delay` | Float | `0.1` | Politeness delay between consecutive requests. |
| `--output` | String | `audit.json`| Destination path for detailed finding output. |
| `--ignore-robots` | Flag | `False` | Bypass `robots.txt` crawl restrictions. |
| `--no-ssl-verify` | Flag | `False` | Disable SSL/TLS certificate verification. |
| `--verbose`, `-v` | Flag | `False` | Enable detailed debug logging. |

### Generated Outputs
1. **`audit.json`**: An array of individual SEO finding objects:
   ```json
   [
     {
       "metric": "missing_canonical",
       "page": "https://example.com/",
       "severity": "medium",
       "evidence": "No <link rel=\"canonical\"> tag was found in the HTML <head>.",
       "suggested_fix": "Add a self-referential or authoritative <link rel=\"canonical\" href=\"...\"> in <head> to prevent duplicate content issues."
     }
   ]
   ```
2. **`audit_summary.json`**: Aggregate statistics including total crawled pages, findings count, severity breakdown, metric breakdown, and URL lists.
3. **Terminal Overview**: Displays formatted findings and crawl statistics.

---

## 7. How to Run Q2 (NAP Consistency Checker)

To run the Name, Address, and Phone consistency checker, supply the `--nap` flag.

### Command
```powershell
python main.py --url "https://example.com" --nap
```

### Optional Crawl Limits
```powershell
python main.py --url "https://example.com" --nap --max-pages 30
```

### Internal Execution Flow
1. Crawls internal pages, prioritizing contact, about, location, and legal pages.
2. Extracts NAP occurrences from JSON-LD (`@graph`, arrays, nested `PostalAddress`), Microdata, and HTML elements (`tel:`, `<address>`, `<title>`, footers).
3. Normalizes phone numbers (E.164/international), addresses (abbreviations expanded, component segmentation), and business names (legal suffixes standardized).
4. Evaluates whether multi-page variations represent cosmetic formatting differences or genuine business discrepancies.
5. Calculates confidence weighted by source quality.
6. Writes results to `nap_report.json` and prints a CLI summary table.

### Example `nap_report.json` Structure
```json
[
  {
    "field": "name",
    "pages_compared": [
      "https://example.com/",
      "https://example.com/contact"
    ],
    "values": [
      "Acme Solutions LLC",
      "Acme Solutions"
    ],
    "normalized_values": [
      "acme solutions"
    ],
    "confidence": 0.95,
    "verdict": "consistent",
    "evidence": [
      {
        "page": "https://example.com/",
        "raw_value": "Acme Solutions LLC",
        "source_type": "json_ld",
        "source_quality": 1.0
      },
      {
        "page": "https://example.com/contact",
        "raw_value": "Acme Solutions",
        "source_type": "html_text",
        "source_quality": 0.5
      }
    ],
    "details": "All normalized business names match after legal suffix normalization."
  },
  {
    "field": "address",
    "pages_compared": [
      "https://example.com/contact"
    ],
    "values": [
      "100 Main St., Suite 200, Seattle, WA 98101"
    ],
    "normalized_values": [
      "100 main street, suite 200, seattle, wa 98101"
    ],
    "confidence": 0.90,
    "verdict": "consistent",
    "evidence": [
      {
        "page": "https://example.com/contact",
        "raw_value": "100 Main St., Suite 200, Seattle, WA 98101",
        "source_type": "json_ld",
        "source_quality": 1.0
      }
    ],
    "details": "All address components and normalized values agree."
  },
  {
    "field": "phone",
    "pages_compared": [
      "https://example.com/",
      "https://example.com/contact"
    ],
    "values": [
      "+1 (555) 019-2834",
      "555-019-2834"
    ],
    "normalized_values": [
      "+15550192834"
    ],
    "confidence": 0.92,
    "verdict": "consistent",
    "evidence": [
      {
        "page": "https://example.com/",
        "raw_value": "+1 (555) 019-2834",
        "source_type": "json_ld",
        "source_quality": 1.0
      },
      {
        "page": "https://example.com/contact",
        "raw_value": "555-019-2834",
        "source_type": "html_tel_link",
        "source_quality": 0.85
      }
    ],
    "details": "All telephone numbers match standard E.164 canonical format."
  }
]
```

---

## 8. How to Run Q3 (Grounded Question Answering)

To run the grounded Question-Answering agent, supply the `--query` (or `-q`) parameter along with `--url`.

### Supported Question Example
```powershell
python main.py --url "https://developers.google.com/search/docs/monitor-debug/search-console-start" --query "What is Google Search Console?"
```

**Output in `answer.json`:**
```json
{
  "query": "What is Google Search Console?",
  "url": "https://developers.google.com/search/docs/monitor-debug/search-console-start",
  "excerpt": "Search Console is a tool from Google that can help anyone with a website to understand how they are performing on Google Search, and what they can do to improve their appearance on search to bring more relevant traffic to their websites."
}
```

### Unsupported Question Example
```powershell
python main.py --url "https://developers.google.com/search/docs/monitor-debug/search-console-start" --query "What is the population of India?"
```

**Output in `answer.json`:**
```json
{
  "query": "What is the population of India?",
  "url": null,
  "excerpt": null
}
```

### Optional Output File Customization
```powershell
python main.py --url "https://example.com" --query "What is the return policy?" --answer-file "custom_answer.json"
```

---

## 9. Output Files

| File Name | Feature | Description | Format |
|---|---|---|---|
| **`audit.json`** | Q1 — SEO Audit | Detailed list of all detected on-page SEO issues, with severity, evidence snippet, and recommended fix. | JSON Array of Finding Objects |
| **`audit_summary.json`** | Q1 — SEO Audit | Executive overview with crawl duration, total pages, severity breakdown, metric breakdown, and URLs. | JSON Object |
| **`nap_report.json`** | Q2 — NAP Checker | Comprehensive consistency report for Name, Address, and Phone fields with verdicts, confidence, and source citations. | JSON Array of Field Report Objects |
| **`answer.json`** | Q3 — Grounded Q&A | Factual answer containing the exact source page URL and verbatim source excerpt (or `null` if unsupported). | JSON Object (`query`, `url`, `excerpt`) |

---

## 10. How to Test the Project

The repository contains **93 automated tests** ensuring zero regressions across all features.

### Run All Tests
```powershell
python -m pytest tests/ -v
```

### Run Q1 Tests Only
```powershell
python -m pytest tests/test_*.py -v
```

### Run Q2 Tests Only
```powershell
python -m pytest tests/nap/ -v
```

### Run Q3 Tests Only
```powershell
python -m pytest tests/qa/ -v
```

### Expected Output
```
============================= 93 passed in 1.25s ==============================
```

---

## 11. Example Testing Workflow

Follow this end-to-end workflow to verify all system components on a clean installation:

```powershell
# 1. Activate environment
.\venv\Scripts\Activate.ps1

# 2. Run the full test suite
python -m pytest tests/ -v

# 3. Execute Q1 SEO audit on a website
python main.py --url "https://example.com" --max-pages 5

# 4. Inspect Q1 outputs
Get-Content audit.json
Get-Content audit_summary.json

# 5. Execute Q2 NAP consistency check
python main.py --url "https://example.com" --nap --max-pages 5

# 6. Inspect Q2 output
Get-Content nap_report.json

# 7. Execute Q3 with a supported question
python main.py --url "https://developers.google.com/search/docs/monitor-debug/search-console-start" --query "What is Google Search Console?" --max-pages 5

# 8. Inspect Q3 supported answer
Get-Content answer.json

# 9. Execute Q3 with an unsupported question
python main.py --url "https://developers.google.com/search/docs/monitor-debug/search-console-start" --query "What is the population of India?" --max-pages 5

# 10. Inspect Q3 null output
Get-Content answer.json
```

---

## 12. Q3 Grounding & Anti-Hallucination Mechanism

The Q3 Question-Answering Agent is strictly designed to eliminate hallucinations:

1. **No External Generative LLMs**: Retrieval is performed deterministically using an in-memory Okapi BM25 engine with passage-tuned parameters ($b = 0.40$), exact phrase matching boosts, and semantic intent classification.
2. **Mention vs. Answer Discrimination**:
   - For definition questions (`"What is X?"`), the system requires the passage to contain an explicit explanatory predicate (`X is...`, `X helps...`, `X allows...`, `X provides...`, `X enables...`, `X serves as...`, `X refers to...`).
   - Incidental mentions where the entity is merely an oblique instrument (`in X`, `using X`, `via X`, `with X`) are penalized and prevented from answering the question.
3. **Strict Support Gating**: If no passage reaches the relevance threshold, or if an entity is mentioned only in passing without an answer predicate, the agent returns `url: null` and `excerpt: null`.
4. **Deterministic Visible-Text Grounding Verification**:
   Before writing `answer.json`, the `GroundingVerifier` extracts the clean visible text from the candidate `ParsedPage` and programmatically asserts:
   ```python
   assert excerpt in visible_text
   ```
   If the excerpt is not a contiguous substring of the source page, it is rejected and `null` is returned.

---

## 13. Q2 Evidence & Confidence Model

Q2 calculates confidence and verdicts deterministically:

- **Source Quality Weighting**:
  - `json_ld`: 1.0 (authoritative structured markup)
  - `microdata`: 0.9 (HTML5 semantic attributes)
  - `html_tel_link`: 0.85 (explicit `tel:` URI)
  - `html_address_tag`: 0.80 (semantic `<address>` container)
  - `html_text`: 0.50 (heuristic body text match)
  - `html_logo_alt`: 0.40 (image alt text)
  - `html_title`: 0.30 (extracted page title brand token)
- **Component-Level Address Parsing**: Addresses are decomposed into `street`, `city`, `state`, and `postal_code`. Two addresses are consistent if their normalized components match, even if formatting or line breaks differ.
- **Harmless Formatting vs. Real Mismatches**:
  - `+1 (555) 019-2834` and `555.019.2834` resolve to canonical `+15550192834` $\to$ `consistent`.
  - `100 Main St.` and `100 Main Street` resolve to `100 main street` $\to$ `consistent`.
  - `Suite 100` vs `Suite 500` or `Dallas` vs `Austin` $\to$ `genuine_mismatch`.

---

## 14. Design Principles

- **Deterministic Processing**: Rule evaluation, normalization, indexing, and ranking produce identical, reproducible results on repeated runs.
- **Evidence-Backed**: Every finding and answer provides a verbatim excerpt from the target DOM or HTTP response.
- **Zero Paid APIs or API Keys**: The system requires no subscription tokens, third-party LLM endpoints, or paid SaaS services.
- **Shared Infrastructure**: Q1, Q2, and Q3 leverage the same modular crawler, normalizer, and parser architecture.
- **Polite & Safe Crawling**: Enforces configurable request delays, crawl depth caps, max page limits, URL cycle detection, and `robots.txt` compliance.

---

## 15. Limitations & Operational Considerations

- **HTTP 403 / Access Restrictions**: If a website or web application firewall (WAF) blocks automated crawlers with an HTTP 403 or Cloudflare challenge, the crawler cannot inspect pages it cannot access.
- **Client-Side JavaScript Rendering**: Sites requiring JavaScript to build links and DOM content rely on Playwright. If Playwright or Chromium is not installed, the crawler operates over raw static HTML, which may yield fewer discoverable links on dynamic SPAs.
- **robots.txt Compliance**: Pages disallowed by the target site's `robots.txt` are skipped by default unless `--ignore-robots` is passed.
- **Scope of Q3 Retrieval**: Q3 only answers questions supported by the pages crawled within `--max-pages` and `--max-depth`. Facts located on uncrawled pages or behind authentication cannot be retrieved.

---

## 16. Troubleshooting

### Issue: `python: command not found` or version mismatch
- **Fix**: Verify Python 3.10+ installation by running `python --version` or `py --version`.

### Issue: Missing dependencies or import errors
- **Fix**: Reinstall requirements in your activated virtual environment:
  ```powershell
  pip install -r requirements.txt
  ```

### Issue: Playwright browser error on SPA websites
- **Fix**: Install the Chromium headless browser binary:
  ```powershell
  playwright install chromium
  ```

### Issue: Target website returns HTTP 403 Forbidden
- **Explanation**: Some websites actively block automated clients via WAFs. The agent logs the 403 status code and safely terminates the crawl.

### Issue: Q3 returns `null` for both `url` and `excerpt`
- **Explanation**: This is the intended behavior when the question is not directly answered by the crawled pages, or when an entity is only mentioned without an explanatory statement.

---

## 17. GitHub Usage

### Pulling Latest Updates
```powershell
git pull origin main
```

### Staging and Pushing Changes
```powershell
git add .
git commit -m "feat: your descriptive commit message"
git push -u origin main
```
*(When pushing on Windows, Git Credential Manager will prompt to authenticate with your GitHub account).*

---

## 18. Submission & Demo Guidelines

- **Source Code Repository**: Contains all source code for `seo_audit/`, `nap_checker/`, `site_qa/`, and `tests/`.
- **Local Execution**: The project is entirely self-contained and runs locally via `python main.py` with no cloud infrastructure required.
- **Sample Reports**: Sample artifacts generated from live crawls are included for reference:
  - `audit.json` & `audit_summary.json` (Q1 SEO Audit)
  - `nap_report.json` (Q2 NAP Consistency Checker)
  - `answer.json` (Q3 Grounded Website Q&A)

---

## 19. Security & Privacy

- **Public Content Only**: This platform is designed solely for analyzing publicly available web pages.
- **No Stored Credentials**: No API keys, passwords, or personal access tokens are stored or required in this repository.
- **Polite Crawling**: Default request intervals and depth boundaries prevent server overload. Always comply with website terms of service and `robots.txt` directives.
