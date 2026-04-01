"""
Safety Compliance Agent — Streamlit UI
A professional interface for analyzing safety documents against OSHA regulations.

Run with: streamlit run app.py
"""

import os
import json
import tempfile
import streamlit as st
from datetime import datetime

from agent.parser import parse_document, parse_text_directly
from agent.analyzer import ComplianceAnalyzer, SEVERITY_LEVELS
from agent.knowledge_base import RegulatoryKnowledgeBase
from agent.report_generator import generate_markdown_report, generate_json_report, save_report


# --- Page Configuration ---
st.set_page_config(
    page_title="Safety Compliance Agent",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Custom Styling ---
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        margin-bottom: 0;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #6b7280;
        margin-top: 0;
    }
    .metric-card {
        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
        border-radius: 12px;
        padding: 1.2rem;
        text-align: center;
        border: 1px solid #dee2e6;
    }
    .finding-critical {
        border-left: 4px solid #dc3545;
        padding-left: 1rem;
        margin: 1rem 0;
        background-color: rgba(220, 53, 69, 0.05);
        padding: 1rem;
        border-radius: 0 8px 8px 0;
    }
    .finding-major {
        border-left: 4px solid #fd7e14;
        padding-left: 1rem;
        margin: 1rem 0;
        background-color: rgba(253, 126, 20, 0.05);
        padding: 1rem;
        border-radius: 0 8px 8px 0;
    }
    .finding-minor {
        border-left: 4px solid #ffc107;
        padding-left: 1rem;
        margin: 1rem 0;
        background-color: rgba(255, 193, 7, 0.05);
        padding: 1rem;
        border-radius: 0 8px 8px 0;
    }
    .finding-advisory {
        border-left: 4px solid #0d6efd;
        padding-left: 1rem;
        margin: 1rem 0;
        background-color: rgba(13, 110, 253, 0.05);
        padding: 1rem;
        border-radius: 0 8px 8px 0;
    }
    .status-badge {
        display: inline-block;
        padding: 0.4rem 1rem;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.95rem;
    }
    .status-non-compliant {
        background-color: #dc3545;
        color: white;
    }
    .status-partial {
        background-color: #ffc107;
        color: #212529;
    }
    .status-compliant {
        background-color: #198754;
        color: white;
    }
</style>
""", unsafe_allow_html=True)


# --- Sidebar ---
with st.sidebar:
    st.title("🛡️ Configuration")
    
    # API Key input
    api_key = st.text_input(
        "Anthropic API Key",
        type="password",
        help="Enter your Anthropic API key. Get one at console.anthropic.com",
        value=os.environ.get("ANTHROPIC_API_KEY", ""),
    )
    
    # Model selection
    model = st.selectbox(
        "Claude Model",
        options=[
            "claude-sonnet-4-20250514",
            "claude-haiku-4-5-20251001",
        ],
        index=0,
        help="Sonnet recommended for thorough analysis. Haiku for faster/cheaper runs.",
    )
    
    st.divider()
    
    # Knowledge Base Info
    st.subheader("📋 Regulatory Knowledge Base")
    try:
        kb = RegulatoryKnowledgeBase()
        st.success(f"**{kb.regulation_body}** — {kb.standard}")
        st.caption(f"Scope: {kb.scope}")
        st.caption(f"Total requirements loaded: {kb.total_requirements}")
        
        numerical = kb.get_critical_numerical_values()
        if numerical:
            with st.expander("Key Numerical Thresholds", expanded=False):
                seen = set()
                for item in numerical:
                    field_name = item["field"].replace("_", " ").title()
                    key = (field_name, item["value"])
                    if key not in seen:
                        seen.add(key)
                        st.text(f"• {field_name}: {item['value']}")
    except Exception as e:
        st.error(f"Failed to load knowledge base: {e}")
    
    st.divider()    
    st.caption("AI Adoption Lead — Skill Assessment Project by Abenanth | GitHub: https://github.com/Abenanth | LinkedIn: https://www.linkedin.com/in/kalyanaabenanthg/")



# --- Main Content ---
st.markdown('<p class="main-header">🛡️ Safety Compliance Agent</p>', unsafe_allow_html=True)
st.markdown(
    '<p class="sub-header">AI-powered compliance analysis for safety procedure documents against OSHA 1926 Subpart M (Fall Protection)</p>',
    unsafe_allow_html=True,
)

st.divider()

# --- Input Section ---
st.subheader("📄 Upload Safety Document")

input_method = st.radio(
    "Choose input method:",
    ["Upload File", "Paste Text", "Use Sample Document"],
    horizontal=True,
)

parsed_doc = None

if input_method == "Upload File":
    uploaded_file = st.file_uploader(
        "Upload a safety document",
        type=["txt", "pdf", "docx"],
        help="Supported formats: TXT, PDF, DOCX",
    )
    
    if uploaded_file:
        # Save to temp file for parsing
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=os.path.splitext(uploaded_file.name)[1]
        ) as tmp:
            tmp.write(uploaded_file.getvalue())
            tmp_path = tmp.name
        
        try:
            parsed_doc = parse_document(tmp_path)
            parsed_doc.filename = uploaded_file.name  # Use original filename
            st.success(f"✅ Parsed **{uploaded_file.name}** — {parsed_doc.word_count} words, {parsed_doc.section_count} sections")
        except Exception as e:
            st.error(f"Error parsing document: {e}")
        finally:
            os.unlink(tmp_path)

elif input_method == "Paste Text":
    pasted_text = st.text_area(
        "Paste safety document content:",
        height=300,
        placeholder="Paste your safety SOP, procedure, or policy document here...",
    )
    
    if pasted_text.strip():
        parsed_doc = parse_text_directly(pasted_text, "pasted_document")
        st.success(f"✅ Parsed pasted text — {parsed_doc.word_count} words, {parsed_doc.section_count} sections")

elif input_method == "Use Sample Document":
    sample_choice = st.selectbox(
        "Choose a sample document:",
        options=[
            "Non-Compliant SOP (Acme Industrial — has deliberate violations)",
            "Compliant SOP (Summit Construction — well-written example)",
        ],
    )
    
    if "Non-Compliant" in sample_choice:
        sample_path = os.path.join(
            os.path.dirname(__file__), "data", "test_documents", "sample_fall_protection_sop.txt"
        )
    else:
        sample_path = os.path.join(
            os.path.dirname(__file__), "data", "test_documents", "compliant_fall_protection_sop.txt"
        )
    
    if os.path.exists(sample_path):
        parsed_doc = parse_document(sample_path)
        st.success(
            f"✅ Loaded sample document: **{parsed_doc.filename}** — "
            f"{parsed_doc.word_count} words, {parsed_doc.section_count} sections"
        )
        
        with st.expander("Preview Sample Document", expanded=False):
            st.text(parsed_doc.full_text[:3000] + "..." if len(parsed_doc.full_text) > 3000 else parsed_doc.full_text)
    else:
        st.error("Sample document not found. Please check the data/test_documents directory.")


# --- Document Preview ---
if parsed_doc:
    with st.expander("📋 Parsed Document Sections", expanded=False):
        for section in parsed_doc.sections:
            st.markdown(f"**Section {section.section_number}: {section.title}**")
            st.text(section.content[:500] + "..." if len(section.content) > 500 else section.content)
            st.divider()

    if parsed_doc.metadata:
        with st.expander("📝 Document Metadata", expanded=False):
            for key, value in parsed_doc.metadata.items():
                st.text(f"{key.replace('_', ' ').title()}: {value}")

# --- Analysis Section ---
st.divider()

col_analyze, col_status = st.columns([3, 1])

with col_analyze:
    analyze_button = st.button(
        "🔍 Analyze for Compliance",
        type="primary",
        disabled=parsed_doc is None or not api_key,
        use_container_width=True,
    )

with col_status:
    if not api_key:
        st.warning("⚠️ Enter API key")
    elif parsed_doc is None:
        st.info("📄 Upload a document")
    else:
        st.success("✅ Ready to analyze")

# --- Run Analysis ---
if analyze_button and parsed_doc and api_key:
    with st.spinner("🔍 Analyzing document for OSHA compliance... This may take 30-60 seconds."):
        try:
            analyzer = ComplianceAnalyzer(api_key=api_key, model=model)
            report = analyzer.analyze(parsed_doc)
            
            # Store in session state
            st.session_state["report"] = report
            st.session_state["analysis_complete"] = True
            
        except Exception as e:
            st.error(f"❌ Analysis failed: {str(e)}")
            st.session_state["analysis_complete"] = False

# --- Display Results ---
if st.session_state.get("analysis_complete") and "report" in st.session_state:
    report = st.session_state["report"]
    
    st.divider()
    st.subheader("📊 Compliance Analysis Results")
    
    # Status Badge
    status = report.overall_compliance_status.upper().replace(" ", "_").replace("-", "_")
    if "NON" in status:
        st.markdown(
            '<span class="status-badge status-non-compliant">🔴 NON-COMPLIANT</span>',
            unsafe_allow_html=True,
        )
    elif "PARTIAL" in status:
        st.markdown(
            '<span class="status-badge status-partial">🟡 PARTIALLY COMPLIANT</span>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<span class="status-badge status-compliant">🟢 COMPLIANT</span>',
            unsafe_allow_html=True,
        )
    
    st.markdown("")
    
    # Executive Summary
    st.markdown(f"**Summary:** {report.summary}")
    st.markdown("")
    
    # Severity Metrics
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Total Findings", report.total_findings)
    with col2:
        st.metric("🔴 Critical", report.critical_count)
    with col3:
        st.metric("🟠 Major", report.major_count)
    with col4:
        st.metric("🟡 Minor", report.minor_count)
    with col5:
        st.metric("🔵 Advisory", report.advisory_count)
    
    st.divider()
    
    # Severity Filter
    severity_filter = st.multiselect(
        "Filter by severity:",
        options=["CRITICAL", "MAJOR", "MINOR", "ADVISORY"],
        default=["CRITICAL", "MAJOR", "MINOR", "ADVISORY"],
    )
    
    # Display Findings
    filtered_findings = [f for f in report.findings if f.severity in severity_filter]
    
    for finding in filtered_findings:
        severity_class = finding.severity.lower()
        
        with st.container():
            st.markdown(
                f'<div class="finding-{severity_class}">',
                unsafe_allow_html=True,
            )
            
            severity_emoji = {
                "CRITICAL": "🔴",
                "MAJOR": "🟠",
                "MINOR": "🟡",
                "ADVISORY": "🔵",
            }
            
            st.markdown(
                f"#### {severity_emoji.get(finding.severity, '⚪')} {finding.finding_id}: {finding.title}"
            )
            st.markdown(f"**Severity:** {finding.severity} &nbsp;|&nbsp; **Document Section:** {finding.document_section}")
            
            col_doc, col_reg = st.columns(2)
            
            with col_doc:
                st.markdown("**📄 Document States:**")
                st.info(finding.document_text)
            
            with col_reg:
                st.markdown(f"**⚖️ OSHA Requirement ({finding.regulation_reference}):**")
                st.warning(finding.regulation_requirement)
            
            st.markdown(f"**💡 Issue:** {finding.description}")
            st.markdown(f"**✅ Recommended Action:** {finding.recommendation}")
            
            st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("")
    
    # --- Export Section ---
    st.divider()
    st.subheader("📥 Export Report")
    
    col_md, col_json = st.columns(2)
    
    with col_md:
        md_content = generate_markdown_report(report)
        st.download_button(
            label="📄 Download Markdown Report",
            data=md_content,
            file_name=f"compliance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
            mime="text/markdown",
            use_container_width=True,
        )
    
    with col_json:
        json_content = generate_json_report(report)
        st.download_button(
            label="📋 Download JSON Report",
            data=json_content,
            file_name=f"compliance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            use_container_width=True,
        )

# --- Footer ---
st.markdown("")
st.divider()
st.caption(
    "⚠️ **Disclaimer:** This tool provides AI-assisted compliance analysis and does not replace "
    "professional regulatory review. All findings should be verified by a qualified safety professional."
)
