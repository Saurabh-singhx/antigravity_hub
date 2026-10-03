import logging
from typing import Any, Dict, List
from config.settings import TRUSTED_SOCIAL_HANDLES

logger = logging.getLogger("AntigravityHub.SocialScanner")


class SocialScannerSkill:
    """Skill to discover verified interview questions and experience digests from tech community handles."""

    def __init__(self):
        self.handles = TRUSTED_SOCIAL_HANDLES

    def get_community_sources_for_tech(self, keywords: List[str]) -> List[Dict[str, Any]]:
        """Returns verified social/community handles relevant to the given tech stack."""
        matched = []
        kw_lower = {k.lower() for k in keywords}

        for item in self.handles:
            tags = {t.lower() for t in item.get("tags", [])}
            overlap = kw_lower.intersection(tags)
            if overlap or "general" in tags or "career" in tags:
                matched.append({
                    "source_type": "tech_handle",
                    "source_name": item["handle"],
                    "source_url": item["url"],
                    "platform": item["platform"],
                    "reliability_score": item["reliability_score"],
                    "matched_tags": list(overlap) if overlap else ["career"],
                })

        return matched
