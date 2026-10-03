import logging
from pathlib import Path
import sqlite3
from typing import Any, Dict, List

from config.settings import AUTO_JOB_APPLY_DB

logger = logging.getLogger("AntigravityHub.JobCollectorAgent")


class JobCollectorAgent:
    """
    Agent responsible for harvesting recently applied jobs from the local
    auto_job_apply database and extracting core target tech stacks and job titles.
    """

    ROLE_TECH_MAPPINGS = {
        "flutter": ["Flutter", "Dart", "Mobile", "State Management", "Widget Lifecycle"],
        "react": ["React", "JavaScript", "TypeScript", "Redux", "Hooks", "Frontend"],
        "mern": ["React", "Node.js", "Express", "MongoDB", "REST APIs", "Full Stack"],
        "python": ["Python", "FastAPI", "Django", "Asyncio", "SQLAlchemy", "Backend"],
        "full stack": ["Full Stack", "React", "Node.js", "SQL", "System Design", "APIs"],
        "software engineer": ["Data Structures", "Algorithms", "System Design", "Core CS"],
        "qa": ["Testing", "Automation", "Pytest", "Selenium", "CI/CD"],
        "ai": ["Python", "LLMs", "Vector DBs", "LangChain", "Prompt Engineering"],
    }

    def __init__(self, db_path: Path = AUTO_JOB_APPLY_DB):
        self.db_path = db_path

    def collect_recent_applied_jobs(self, limit: int = 15) -> List[Dict[str, Any]]:
        """Reads recent applications from auto_job_apply database."""
        jobs = []
        if self.db_path.exists():
            try:
                conn = sqlite3.connect(str(self.db_path))
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()
                cur.execute(
                    """
                    SELECT id, platform, job_title, company, location, status, applied_at
                    FROM applications
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (limit,),
                )
                rows = cur.fetchall()
                for r in rows:
                    job_dict = dict(r)
                    job_dict["extracted_keywords"] = self._extract_keywords(job_dict["job_title"])
                    jobs.append(job_dict)
                conn.close()
                logger.info(f"Collected {len(jobs)} recent applied jobs from {self.db_path}")
            except Exception as e:
                logger.warning(f"Error reading applied jobs from {self.db_path}: {e}")

        # Fallback profile if auto_job_apply is empty or not yet run
        if not jobs:
            logger.info("Using default high-yield applied tech profile.")
            jobs = [
                {
                    "id": 1,
                    "platform": "wellfound",
                    "job_title": "Full Stack Engineer (+Flutter)",
                    "company": "TechStartup",
                    "extracted_keywords": ["Flutter", "Dart", "React", "Full Stack", "Mobile"],
                },
                {
                    "id": 2,
                    "platform": "naukri",
                    "job_title": "Full Stack Engineer (MERN)",
                    "company": "Innovations Lab",
                    "extracted_keywords": ["React", "Node.js", "MongoDB", "Express", "Full Stack"],
                },
                {
                    "id": 3,
                    "platform": "linkedin",
                    "job_title": "AI Full Stack Engineer - Python",
                    "company": "Cognitive AI",
                    "extracted_keywords": ["Python", "FastAPI", "LLMs", "System Design", "Backend"],
                },
            ]

        return jobs

    def _extract_keywords(self, title: str) -> List[str]:
        """Extracts technical keywords from job title."""
        title_lower = title.lower()
        extracted = []
        for role_key, tech_list in self.ROLE_TECH_MAPPINGS.items():
            if role_key in title_lower:
                extracted.extend(tech_list)

        if not extracted:
            extracted = ["Full Stack", "Algorithms", "System Design", "Python", "JavaScript"]

        return list(dict.fromkeys(extracted))  # Deduplicate while preserving order
