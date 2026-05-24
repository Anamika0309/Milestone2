# Problem Statement: Mutual Fund FAQ Assistant (Facts-Only Q&A)

## Overview
The objective of this project is to build a facts-only FAQ assistant for mutual fund schemes, using Groww as the reference product context. The assistant will answer objective, verifiable queries related to mutual funds by retrieving information exclusively from official public sources, such as AMC (Asset Management Company) websites, AMFI, and SEBI.

The system must strictly avoid providing investment advice, opinions, or recommendations. Every response must include a single, clear source link and adhere to defined constraints around clarity, accuracy, and compliance.

## Objective
Design and implement a lightweight Retrieval-Augmented Generation (RAG)-based assistant that:
- Answers factual queries about mutual fund schemes
- Uses a curated corpus of official documents (specifically 5 whitelisted Groww URLs in this iteration)
- Provides concise, source-backed responses

## Target Users
- Retail investors comparing mutual fund schemes
- Customer support and content teams handling repetitive mutual fund queries

## Scope of Work

### 1. Corpus Definition
For this iteration, the corpus is strictly limited to the following **5 Groww HDFC scheme URLs**:
1. **HDFC Mid Cap Fund - Direct Growth**
   `https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth`
2. **HDFC Equity Fund - Direct Growth**
   `https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth`
3. **HDFC Focused Fund - Direct Growth**
   `https://groww.in/mutual-funds/hdfc-focused-fund-direct-growth`
4. **HDFC ELSS Tax Saver - Direct Plan Growth**
   `https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth`
5. **HDFC Large Cap Fund - Direct Growth**
   `https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth`

> [!IMPORTANT]
> The corpus is strictly closed. No other URLs (SEBI, AMFI, KIM/SID PDFs, or AMC help pages) are ingested. Every fact returned must be present in these 5 URLs.

### 2. FAQ Assistant Requirements
The assistant must:
- Answer facts-only queries, such as:
  - Expense ratio of a scheme
  - Exit load details
  - Minimum SIP amount
  - ELSS lock-in period
  - Riskometer classification
  - Benchmark index
- Ensure:
  - Each response is limited to a maximum of **3 sentences**.
  - Each response includes **exactly one citation link** from the whitelist on successful factual answers.
  - Each response includes a footer: `Last updated from sources: YYYY-MM-DD`

### 3. Refusal Handling
The assistant must refuse non-factual, advisory, comparative, or predictive queries, such as:
- *"Should I invest in this fund?"*
- *"Which fund is better?"*
- *"How much returns will HDFC Mid Cap give next year?"*

Refusal responses should:
- Be polite and clearly worded.
- Reinforce the facts-only limitation.
- Provide a relevant educational link from the 5 whitelisted URLs (e.g., the scheme URL most relevant to the query).

### 4. User Interface (Minimal)
The solution should include a simple interface with:
- A welcome message
- Three example questions
- A visible disclaimer: `"Facts-only. No investment advice."`

---

## Constraints

### 1. Data and Sources
- Use only official public sources (Groww pages representing the HDFC schemes in this iteration).
- Do not use third-party blogs or aggregator websites.
- A cited URL must match one of the 5 whitelisted URLs exactly.

### 2. Privacy and Security
Do not collect, store, or process Personally Identifiable Information (PII):
- PAN or Aadhaar numbers
- Account numbers
- OTPs
- Email addresses or phone numbers

Any query containing PII must be immediately deflected with a standard block template and **exactly zero URLs**.

### 3. Content Restrictions
- **No investment advice or recommendations.**
- **No performance comparisons or return calculations.**
- For performance-related queries, provide a link to the official scheme page only without speculative calculations.

### 4. Transparency
- Responses must be short, factual, and verifiable.
- Every answer must include a source link and last updated date.

---

## Expected Deliverables
1. **README Document**: Setup instructions, selected AMC, schemes, architecture overview, known limitations.
2. **Disclaimer Snippet**: `"Facts-only. No investment advice."`
3. **Clean Codebase**: Separated phase-wise components representing each step of development.

## Success Criteria
1. Accurate retrieval of factual mutual fund information.
2. Strict adherence to facts-only responses (sentence count $\leq 3$).
3. Consistent inclusion of valid source citations.
4. Proper refusal of advisory, predictive, and comparative queries.
5. PII detection and prevention of data leakages.
