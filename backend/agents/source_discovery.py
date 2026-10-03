import logging
from typing import Any, Dict, List

from agents.skills.github_scanner import GitHubScannerSkill
from agents.skills.safety_guard import SafetyGuardSkill
from agents.skills.social_scanner import SocialScannerSkill

logger = logging.getLogger("AntigravityHub.SourceDiscoveryAgent")


class SourceDiscoveryAgent:
    """
    Agent responsible for finding reliable, trending GitHub repositories
    and vetted social media handles for the applied roles, with strict safety vetting.
    """

    def __init__(self):
        self.github_scanner = GitHubScannerSkill()
        self.social_scanner = SocialScannerSkill()

    def discover_safe_sources_for_jobs(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Finds vetted sources for the given list of target applied jobs."""
        all_keywords = set()
        for j in jobs:
            for kw in j.get("extracted_keywords", []):
                all_keywords.add(kw)

        kw_list = list(all_keywords)
        logger.info(f"Discovering sources for tech stacks: {kw_list[:8]}...")

        # 1. Discover GitHub repositories
        github_repos = self.github_scanner.find_repos_for_tech(kw_list)

        # 2. Discover Verified Social Handles & Tech Communities
        social_handles = self.social_scanner.get_community_sources_for_tech(kw_list)

        # 3. Filter through SafetyGuard
        vetted_sources = []
        for repo in github_repos:
            is_safe, reason = SafetyGuardSkill.is_repo_reliable(repo["name"], repo.get("stars"))
            if is_safe:
                vetted_sources.append({
                    "source_type": "github_repo",
                    "source_name": repo["name"],
                    "source_url": repo["url"],
                    "raw_base": repo.get("raw_base"),
                    "stars": repo.get("stars", 0),
                    "reliability_score": min(1.0, 0.85 + (repo.get("stars", 0) / 500000)),
                    "tags": repo.get("tags", []),
                })
            else:
                logger.warning(f"SafetyGuard discarded repo '{repo['name']}': {reason}")

        for handle in social_handles:
            vetted_sources.append({
                "source_type": "tech_handle",
                "source_name": f"{handle['platform']} ({handle['source_name']})",
                "source_url": handle["source_url"],
                "stars": None,
                "reliability_score": handle["reliability_score"],
                "tags": handle["matched_tags"],
            })

        logger.info(f"Discovered {len(vetted_sources)} verified, safe sources.")
        return vetted_sources
