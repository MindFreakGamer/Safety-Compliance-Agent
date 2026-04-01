# 🛡️ Safety Compliance Agent

**AI-powered regulatory compliance analysis for workplace safety documents.**

An intelligent agent that evaluates safety procedure documents (SOPs) against OSHA 29 CFR 1926 Subpart M (Fall Protection) requirements — flagging compliance gaps with specific citations, severity ratings, and actionable recommendations.

Built as a skill assessment for the **AI Adoption Lead** role .

---

## 🎯 What It Does

The agent accepts a safety document as input and:

1. **Parses** the document into logical sections (supports PDF, DOCX, TXT)
2. **Identifies** applicable OSHA Fall Protection requirements
3. **Analyzes** each section against a structured regulatory knowledge base with specific numerical thresholds
4. **Flags** compliance issues: incorrect values, missing elements, outdated practices, vague language, contradictions
5. **Produces** a structured compliance report with severity ratings that a non-technical safety manager can act on

### Compliance Issues Detected

| Category | Examples |
|----------|----------|
| Incorrect values | Wrong fall protection trigger height (e.g., 10 ft instead of 6 ft) |
| Missing requirements | No rescue plan, missing training topics, absent equipment specs |
| Prohibited practices | Body belts for fall arrest (prohibited since 1998) |
| Weak language | "Should" instead of "shall" where compliance is mandatory |
| Vague specifications | "Reasonable distance" instead of the 6-foot maximum free fall |
| Outdated references | Standards that have been superseded or revised |

---

## 🏗️ Architecture

```
┌─────────────────┐     ┌──────────────────────┐
│  Safety Document │     │  OSHA 1926 Subpart M  │
│  (PDF/DOCX/TXT)  │     │  Knowledge Base (JSON) │
└────────┬────────┘     └──────────┬───────────┘
         │                         │
         ▼                         ▼
┌─────────────────┐     ┌──────────────────────┐
│ Document Parser  │────▶│  Claude Analysis      │
│ (Text Extraction)│     │  Engine               │
└─────────────────┘     │  (Section-by-section   │
                        │   compliance check)    │
                        └──────────┬───────────┘
                                   │
                                   ▼
                        ┌──────────────────────┐
                        │  Compliance Report    │
                        │  (Markdown / JSON)    │
                        │  • Severity ratings   │
                        │  • OSHA citations     │
                        │  • Corrective actions │
                        └──────────────────────┘
```

### Key Design Decisions

- **Structured Knowledge Base over LLM memory**: Regulations are stored as structured JSON with exact numerical values, section citations, and known violation patterns — not relying on the LLM to recall regulations from training data. This ensures accuracy and makes the system auditable.

- **Section-by-section analysis**: Documents are parsed into logical sections and analyzed individually. This improves accuracy by focusing Claude's attention and makes findings traceable to specific document locations.

- **Temperature 0 for deterministic output**: Compliance analysis must be consistent and reproducible. Creative variation would be a liability here.

- **Severity classification**: Findings are rated CRITICAL / MAJOR / MINOR / ADVISORY with specific definitions, so safety managers can prioritize corrective actions.

- **Text-only parsing (v1)**: Extracts text content from documents. Vision-based parsing for diagrams and flowcharts is planned for v2 (see Roadmap).

---

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- An [Anthropic API key](https://console.anthropic.com/)

### Installation

```bash
# Clone the repository
git clone https://github.com/Abenanth/safety-compliance-agent.git
cd safety-compliance-agent

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set your API key
export ANTHROPIC_API_KEY="your-api-key-here"
# On Windows: set ANTHROPIC_API_KEY=your-api-key-here
```

### Run the Application

```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`.

### Usage

1. Enter your Anthropic API key in the sidebar (or set it as an environment variable)
2. Choose an input method:
   - **Upload File**: Upload a PDF, DOCX, or TXT safety document
   - **Paste Text**: Paste document content directly
   - **Use Sample Document**: Load the included test SOP
3. Click **"Analyze for Compliance"**
4. Review the findings (filterable by severity)
5. Download the report as Markdown or JSON

---

## 📁 Project Structure

```
safety-compliance-agent/
├── app.py                          # Streamlit UI application
├── agent/
│   ├── __init__.py
│   ├── parser.py                   # Document parsing (PDF, DOCX, TXT)
│   ├── knowledge_base.py           # OSHA regulatory knowledge base loader
│   ├── analyzer.py                 # Claude-powered compliance analysis engine
│   └── report_generator.py         # Markdown/JSON report generation
├── data/
│   ├── osha_1926_subpart_m.json    # Structured regulatory requirements
│   └── test_documents/
│       └── sample_fall_protection_sop.txt  and other live documents 
├── Tested_output/
│   └── sample_compliance_report.md # Example report output
├── requirements.txt
├── .env.example
└── README.md
```

---

## 📊 Sample Output

A sample compliance report is included in `sample_output/sample_compliance_report.md`. The test document (`sample_fall_protection_sop.txt`) is a realistic fall protection SOP with deliberate compliance gaps including:

- 10-foot trigger height instead of the OSHA-required 6 feet
- 36-inch guardrail height instead of 42 inches (±3")
- 3,000 lb anchorage strength instead of 5,000 lbs
- Body belts allowed for fall arrest (prohibited since 1998)
- Missing rescue procedures, incomplete training documentation, and more

---

## ⚠️ Limitations & Error Handling

### Current Limitations
- **Text-only parsing**: Does not analyze images, diagrams, or flowcharts embedded in documents
- **Single regulation body**: Currently covers only OSHA 1926 Subpart M (Fall Protection). Does not cross-reference ANSI Z359 or CSA standards
- **English only**: Document parsing and analysis are limited to English-language documents
- **No version tracking**: Does not track regulation amendment dates or compare against historical versions

### Error Handling
- **Malformed documents**: The parser gracefully handles documents that don't follow standard section numbering by treating the entire text as a single section
- **API failures**: Network errors and API rate limits are caught and reported to the user with clear messages
- **Invalid JSON response**: The analyzer includes fallback parsing logic if Claude's response isn't perfectly formatted JSON
- **Missing API key**: The UI prevents analysis from running without a valid API key configured

### Where the Agent May Struggle
- Documents with highly non-standard formatting
- SOPs that reference regulations indirectly without naming specific standards
- Very long documents (>50 pages) may require chunking strategies to stay within context limits

---

## 🗺️ Roadmap: What V2 Would Look Like

1. **Vision-based document parsing**: Use Claude's vision API to send PDF pages as images, enabling analysis of diagrams, technical drawings, dimensional specifications, and flowcharts
2. **Multi-regulation support**: Add ANSI Z359, CSA Z259, and additional OSHA subparts (scaffolding, ladders, electrical)
3. **Regulatory change detection**: Monitor Federal Register for OSHA updates and automatically flag which courses/documents are affected
4. **Batch processing**: Analyze an entire library of safety documents in one run, producing a dashboard-level compliance overview
5. **Confidence scoring**: Each finding would include a confidence score so reviewers know which items to prioritize for human verification
6. **Integration with BIS LMS**: Connect directly to the BIS training platform to flag non-compliant course content automatically
7. **Audit trail**: Track analysis history, document versions, and remediation status

---

## 🛠️ Technology Stack

| Component | Technology | Why |
|-----------|-----------|-----|
| LLM | Claude (Anthropic) | Strong document analysis, structured output, consistent reasoning |
| UI | Streamlit | Fast prototyping, professional appearance, built-in file handling |
| Document Parsing | pdfplumber, python-docx | Reliable text extraction from common document formats |
| Language | Python | Standard for AI/ML workflows, broad library ecosystem |

---

## 📄 License

This project was created as a skill assessment exercise. All regulatory information is sourced from publicly available OSHA standards.

---

