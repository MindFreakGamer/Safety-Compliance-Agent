"""
Compliance Analysis Engine
Uses Claude API to analyze safety documents against OSHA regulatory requirements.

Design Decision: We send the full regulatory knowledge base as context with each
analysis request rather than relying on Claude's training data. This ensures the
agent checks against specific, structured requirements with exact numerical values,
not recalled (potentially outdated or imprecise) regulation knowledge.

Architecture:
1. Send document sections + regulatory KB to Claude
2. Claude performs section-by-section analysis
3. Returns structured findings with severity, citations, and recommendations
"""

import json
import os
import re
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime

import anthropic

from .parser import ParsedDocument
from .knowledge_base import RegulatoryKnowledgeBase


# Severity levels for compliance findings
SEVERITY_LEVELS = {
    "CRITICAL": {
        "description": "Direct violation of a specific OSHA requirement with potential for serious injury or death",
        "color": "red",
        "action_required": "Immediate corrective action required before work continues",
    },
    "MAJOR": {
        "description": "Incorrect specification, missing required element, or practice that contradicts OSHA standards",
        "color": "orange",
        "action_required": "Corrective action required before next use of this procedure",
    },
    "MINOR": {
        "description": "Vague language, incomplete coverage, or weak phrasing where specifics are required by OSHA",
        "color": "yellow",
        "action_required": "Should be addressed in the next document revision",
    },
    "ADVISORY": {
        "description": "Best practice recommendation or area where additional detail would strengthen compliance posture",
        "color": "blue",
        "action_required": "Recommended improvement — not a direct violation",
    },
}


@dataclass
class ComplianceFinding:
    """A single compliance issue found in the document."""
    finding_id: str
    severity: str  # CRITICAL, MAJOR, MINOR, ADVISORY
    title: str
    description: str
    document_section: str
    document_text: str  # The specific text from the document
    regulation_reference: str  # OSHA section number
    regulation_requirement: str  # What the regulation actually requires
    recommendation: str

    def to_dict(self) -> dict:
        return {
            "finding_id": self.finding_id,
            "severity": self.severity,
            "title": self.title,
            "description": self.description,
            "document_section": self.document_section,
            "document_text": self.document_text,
            "regulation_reference": self.regulation_reference,
            "regulation_requirement": self.regulation_requirement,
            "recommendation": self.recommendation,
        }


@dataclass
class ComplianceReport:
    """Complete compliance analysis report."""
    document_name: str
    analysis_date: str
    regulation_standard: str
    total_findings: int = 0
    critical_count: int = 0
    major_count: int = 0
    minor_count: int = 0
    advisory_count: int = 0
    findings: list = field(default_factory=list)
    summary: str = ""
    overall_compliance_status: str = ""
    document_metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "document_name": self.document_name,
            "analysis_date": self.analysis_date,
            "regulation_standard": self.regulation_standard,
            "overall_compliance_status": self.overall_compliance_status,
            "summary": self.summary,
            "total_findings": self.total_findings,
            "severity_breakdown": {
                "critical": self.critical_count,
                "major": self.major_count,
                "minor": self.minor_count,
                "advisory": self.advisory_count,
            },
            "findings": [f.to_dict() for f in self.findings],
            "document_metadata": self.document_metadata,
        }


class ComplianceAnalyzer:
    """
    Analyzes safety documents for regulatory compliance using Claude.
    
    The analyzer sends document content along with the structured regulatory
    knowledge base to Claude, which performs a detailed section-by-section
    compliance check and returns structured findings.
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "claude-sonnet-4-20250514"):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Anthropic API key is required. Set ANTHROPIC_API_KEY environment variable "
                "or pass api_key parameter."
            )
        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.model = model
        self.kb = RegulatoryKnowledgeBase()

    def analyze(self, document: ParsedDocument) -> ComplianceReport:
        """
        Perform full compliance analysis on a parsed document.
        
        Returns a ComplianceReport with all findings, severity ratings,
        and recommendations.
        """
        # Build the analysis prompt
        prompt = self._build_analysis_prompt(document)

        # Call Claude API
        response = self.client.messages.create(
            model=self.model,
            max_tokens=8000,
            temperature=0,  # Deterministic for compliance analysis
            system=self._get_system_prompt(),
            messages=[{"role": "user", "content": prompt}],
        )

        # Parse Claude's response into structured findings
        response_text = response.content[0].text
        findings = self._parse_findings(response_text)

        # Build the report
        report = self._build_report(document, findings, response_text)

        return report

    def _get_system_prompt(self) -> str:
        """System prompt that defines Claude's role and output format."""
        return """You are a regulatory compliance analyst specializing in workplace safety standards. Your role is to analyze safety procedure documents against specific OSHA regulations and identify compliance gaps.

CRITICAL INSTRUCTIONS:
1. You MUST check every claim, number, and specification in the document against the regulatory requirements provided.
2. Every finding MUST cite the specific OSHA section number (e.g., 1926.502(b)(1)).
3. You must identify: incorrect values, missing requirements, outdated practices, contradictions, and vague language where specifics are legally required.
4. Be thorough — missing a critical compliance gap could lead to workplace injuries.
5. Do NOT invent or hallucinate regulations. Only cite requirements from the knowledge base provided.

OUTPUT FORMAT:
You must respond with a valid JSON object. No text before or after the JSON.
CRITICAL JSON RULES:
- All strings must use proper JSON escaping (use \\" for quotes inside strings)
- Do not use smart quotes or special characters
- Keep all string values on a single line (no line breaks inside strings)
- Ensure every string is properly closed with a quote
- Test that your JSON is valid before responding
The JSON must follow this exact structure:

{
    "summary": "Brief overall assessment (2-3 sentences)",
    "overall_compliance_status": "NON-COMPLIANT | PARTIALLY_COMPLIANT | COMPLIANT",
    "findings": [
        {
            "finding_id": "F001",
            "severity": "CRITICAL | MAJOR | MINOR | ADVISORY",
            "title": "Short descriptive title",
            "description": "Detailed explanation of the compliance issue",
            "document_section": "Section number/title from the document where the issue was found",
            "document_text": "The exact text or quote from the document that is non-compliant",
            "regulation_reference": "OSHA section number (e.g., 1926.501(b)(1))",
            "regulation_requirement": "What the regulation actually requires",
            "recommendation": "Specific corrective action to achieve compliance"
        }
    ]
}

SEVERITY GUIDELINES:
- CRITICAL: Direct violation of a specific numerical requirement or prohibition (wrong height threshold, prohibited equipment allowed, etc.)
- MAJOR: Missing required element, incorrect specification, or practice contradicting standards
- MINOR: Vague language where specifics are required, incomplete coverage of a topic, weak phrasing (e.g., "should" instead of "shall")
- ADVISORY: Best practice recommendation or area for improvement beyond minimum compliance"""

    def _build_analysis_prompt(self, document: ParsedDocument) -> str:
        """Build the full analysis prompt with document content and regulatory KB."""
        kb_text = self.kb.format_for_prompt()

        prompt = f"""Analyze the following safety procedure document for compliance with OSHA 29 CFR 1926 Subpart M (Fall Protection).

===== REGULATORY REQUIREMENTS (Knowledge Base) =====
{kb_text}

===== DOCUMENT TO ANALYZE =====
Filename: {document.filename}
Document Type: {document.file_type}
Word Count: {document.word_count}
Number of Sections: {document.section_count}

--- Full Document Text ---
{document.full_text}

===== ANALYSIS INSTRUCTIONS =====
1. Go through EVERY section of the document systematically.
2. For each section, check all claims, numbers, and specifications against the regulatory requirements above.
3. Pay special attention to:
   - Numerical values (heights, forces, distances) — check each one against the regulation
   - Required elements that may be missing entirely from the document
   - Definitions that may not match OSHA definitions
   - Language strength ("should" vs "shall") where OSHA mandates compliance
   - Prohibited practices that the document may incorrectly allow
   - Training requirements completeness
   - Documentation/record-keeping requirements
4. For each finding, quote the specific problematic text from the document.
5. Cite the exact OSHA section number for each finding.

Respond with ONLY the JSON object. No other text."""

        return prompt

    def _parse_findings(self, response_text: str) -> list:
        """Parse Claude's JSON response into ComplianceFinding objects."""
        # Clean response - sometimes Claude wraps in markdown code blocks
        cleaned = response_text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        # Remove control characters that can break JSON parsing
        cleaned = re.sub(r'[\x00-\x1f\x7f]', lambda m: ' ' if m.group() not in ('\n', '\r', '\t') else m.group(), cleaned)

        data = None

        # Attempt 1: Direct parse
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        # Attempt 2: Extract JSON object from surrounding text
        if data is None:
            start = cleaned.find("{")
            end = cleaned.rfind("}") + 1
            if start >= 0 and end > start:
                try:
                    data = json.loads(cleaned[start:end])
                except json.JSONDecodeError:
                    pass

        # Attempt 3: Fix common JSON issues (unescaped quotes in strings)
        if data is None:
            try:
                # Replace smart quotes with regular quotes
                fixed = cleaned.replace('\u201c', '\\"').replace('\u201d', '\\"')
                fixed = fixed.replace('\u2018', "\\'").replace('\u2019', "\\'")
                # Try to fix unescaped quotes inside string values
                # This regex finds strings and escapes internal quotes
                fixed = re.sub(
                    r'(?<=: ")(.*?)(?="[,\n\r\t ]*["\}\]])',
                    lambda m: m.group(0).replace('"', '\\"') if m.group(0).count('"') > 0 else m.group(0),
                    fixed,
                    flags=re.DOTALL
                )
                start = fixed.find("{")
                end = fixed.rfind("}") + 1
                if start >= 0 and end > start:
                    data = json.loads(fixed[start:end])
            except (json.JSONDecodeError, Exception):
                pass

        # Attempt 4: Use Claude to fix its own JSON (retry with smaller prompt)
        if data is None:
            try:
                repair_response = self.client.messages.create(
                    model=self.model,
                    max_tokens=8000,
                    temperature=0,
                    messages=[{
                        "role": "user",
                        "content": f"The following JSON has syntax errors. Fix ONLY the JSON syntax (escape quotes, fix commas, etc.) and return valid JSON. Do not change any content. Return ONLY the fixed JSON, no other text.\n\n{response_text}"
                    }],
                )
                repair_text = repair_response.content[0].text.strip()
                if repair_text.startswith("```json"):
                    repair_text = repair_text[7:]
                if repair_text.startswith("```"):
                    repair_text = repair_text[3:]
                if repair_text.endswith("```"):
                    repair_text = repair_text[:-3]
                repair_text = repair_text.strip()
                start = repair_text.find("{")
                end = repair_text.rfind("}") + 1
                if start >= 0 and end > start:
                    data = json.loads(repair_text[start:end])
            except Exception:
                pass

        if data is None:
            raise ValueError(
                f"Could not parse Claude's response as JSON after multiple attempts.\n"
                f"Response preview: {response_text[:500]}"
            )

        self._raw_response = data

        findings = []
        for item in data.get("findings", []):
            finding = ComplianceFinding(
                finding_id=item.get("finding_id", ""),
                severity=item.get("severity", "ADVISORY"),
                title=item.get("title", ""),
                description=item.get("description", ""),
                document_section=item.get("document_section", ""),
                document_text=item.get("document_text", ""),
                regulation_reference=item.get("regulation_reference", ""),
                regulation_requirement=item.get("regulation_requirement", ""),
                recommendation=item.get("recommendation", ""),
            )
            findings.append(finding)

        return findings

    def _build_report(
        self, document: ParsedDocument, findings: list, raw_response: str
    ) -> ComplianceReport:
        """Build a ComplianceReport from the analysis findings."""
        # Count by severity
        severity_counts = {"CRITICAL": 0, "MAJOR": 0, "MINOR": 0, "ADVISORY": 0}
        for f in findings:
            if f.severity in severity_counts:
                severity_counts[f.severity] += 1

        # Get summary from raw response
        raw_data = getattr(self, "_raw_response", {})
        summary = raw_data.get("summary", "Analysis complete.")
        status = raw_data.get("overall_compliance_status", "UNKNOWN")

        report = ComplianceReport(
            document_name=document.filename,
            analysis_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            regulation_standard=self.kb.standard,
            total_findings=len(findings),
            critical_count=severity_counts["CRITICAL"],
            major_count=severity_counts["MAJOR"],
            minor_count=severity_counts["MINOR"],
            advisory_count=severity_counts["ADVISORY"],
            findings=findings,
            summary=summary,
            overall_compliance_status=status,
            document_metadata=document.metadata,
        )

        return report
