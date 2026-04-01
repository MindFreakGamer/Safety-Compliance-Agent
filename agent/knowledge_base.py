"""
Knowledge Base Module
Loads and provides access to structured OSHA regulatory requirements.

Design Decision: Regulations are stored as structured JSON rather than raw text.
This gives the AI agent specific numerical values, section citations, and known
violation patterns to check against — much more effective than asking an LLM to
recall regulations from training data alone.
"""

import json
import os
from typing import Optional


class RegulatoryKnowledgeBase:
    """Loads and provides access to OSHA 1926 Subpart M requirements."""

    def __init__(self, kb_path: Optional[str] = None):
        if kb_path is None:
            kb_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                "data",
                "osha_1926_subpart_m.json",
            )
        
        with open(kb_path, "r") as f:
            self._data = json.load(f)

        self._all_requirements = self._flatten_requirements()

    @property
    def regulation_body(self) -> str:
        return self._data.get("regulation_body", "OSHA")

    @property
    def standard(self) -> str:
        return self._data.get("standard", "")

    @property
    def scope(self) -> str:
        return self._data.get("scope", "")

    @property
    def all_requirements(self) -> list:
        return self._all_requirements

    @property
    def total_requirements(self) -> int:
        return len(self._all_requirements)

    def _flatten_requirements(self) -> list:
        """Flatten all requirements from all sections into a single list."""
        requirements = []
        for section_id, section_data in self._data.get("sections", {}).items():
            for req in section_data.get("requirements", []):
                req_copy = dict(req)
                req_copy["parent_section"] = section_id
                req_copy["parent_title"] = section_data.get("title", "")
                requirements.append(req_copy)
        return requirements

    def get_section(self, section_id: str) -> Optional[dict]:
        """Get a specific section by ID (e.g., '1926.501')."""
        return self._data.get("sections", {}).get(section_id)

    def get_requirements_by_keywords(self, keywords: list) -> list:
        """Find requirements matching any of the given keywords."""
        matches = []
        keywords_lower = [kw.lower() for kw in keywords]

        for req in self._all_requirements:
            req_keywords = [k.lower() for k in req.get("keywords", [])]
            req_text = req.get("requirement", "").lower()

            for kw in keywords_lower:
                if kw in req_text or any(kw in rk for rk in req_keywords):
                    matches.append(req)
                    break

        return matches

    def get_critical_numerical_values(self) -> list:
        """Extract all requirements that have specific numerical thresholds."""
        numerical = []
        numerical_fields = [
            "trigger_height_feet",
            "guardrail_top_rail_height_inches",
            "top_rail_force_pounds",
            "midrail_force_pounds",
            "anchorage_strength_pounds",
            "max_free_fall_feet",
            "max_deceleration_distance_feet",
            "max_arrest_force_pounds",
            "max_net_distance_feet",
            "warning_line_distance_feet",
            "toeboard_min_height_inches",
            "toeboard_force_pounds",
            "wire_rope_flag_interval_feet",
        ]

        for req in self._all_requirements:
            for field in numerical_fields:
                if field in req:
                    numerical.append({
                        "id": req.get("id"),
                        "section": req.get("section", req.get("parent_section")),
                        "field": field,
                        "value": req[field],
                        "requirement": req.get("requirement"),
                    })

        return numerical

    def format_for_prompt(self) -> str:
        """
        Format the entire knowledge base as a structured text block
        suitable for inclusion in an LLM prompt.
        """
        lines = []
        lines.append(f"REGULATORY STANDARD: {self.standard}")
        lines.append(f"SCOPE: {self.scope}")
        lines.append(f"REGULATION BODY: {self.regulation_body}")
        lines.append("")

        for section_id, section_data in self._data.get("sections", {}).items():
            lines.append(f"{'='*80}")
            lines.append(f"SECTION {section_id}: {section_data.get('title', '')}")
            lines.append(f"{'='*80}")

            for req in section_data.get("requirements", []):
                section_ref = req.get("section", section_id)
                lines.append(f"\n[{section_ref}] (ID: {req['id']})")
                lines.append(f"Requirement: {req['requirement']}")

                # Add numerical values if present
                for key, value in req.items():
                    if key.endswith(("_feet", "_inches", "_pounds")) and isinstance(value, (int, float)):
                        readable_key = key.replace("_", " ").title()
                        lines.append(f"  >> {readable_key}: {value}")

                if "acceptable_range_inches" in req:
                    r = req["acceptable_range_inches"]
                    lines.append(f"  >> Acceptable Range: {r['min']} to {r['max']} inches")

                if "net_extension_table" in req:
                    lines.append("  >> Net Extension Requirements:")
                    for height, ext in req["net_extension_table"].items():
                        lines.append(f"     - {height.replace('_', ' ')}: {ext}")

                if "certification_requirements" in req:
                    lines.append("  >> Required Certification Elements:")
                    for item in req["certification_requirements"]:
                        lines.append(f"     - {item}")

                if "required_training_topics" in req:
                    lines.append("  >> Required Training Topics:")
                    for topic in req["required_training_topics"]:
                        lines.append(f"     - {topic}")

                if "retraining_triggers" in req:
                    lines.append("  >> Retraining Triggers:")
                    for trigger in req["retraining_triggers"]:
                        lines.append(f"     - {trigger}")

                if "common_violations" in req:
                    lines.append("  >> Common Violations to Watch For:")
                    for violation in req["common_violations"]:
                        lines.append(f"     ! {violation}")

            lines.append("")

        return "\n".join(lines)
