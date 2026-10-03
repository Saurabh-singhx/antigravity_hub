import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
SCREENSHOTS_DIR = DATA_DIR / "screenshots"
DB_PATH = DATA_DIR / "hub.db"
ACTIVE_PORT_FILE = DATA_DIR / "active_port.txt"

DATA_DIR.mkdir(parents=True, exist_ok=True)
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

# External job applications database from auto_job_apply
AUTO_JOB_APPLY_DB = Path("/home/saurabh/coding/auto_job_apply/data/job_applications.db")

# Network Settings
HUB_PORT = int(os.environ.get("HUB_PORT", 8765))
HUB_HOST = os.environ.get("HUB_HOST", "0.0.0.0")

# Daily QnA Scheduling Slots
# Slot 1 (Morning): 04:00 - 11:00 (4:00 AM - 10:59 AM)
# Slot 2 (Afternoon): 11:00 - 17:00 (11:00 AM - 4:59 PM)
# Slot 3 (Evening): 17:00 - 24:00 (5:00 PM - 11:59 PM)
# Night (00:00 - 04:00): Quiet period (no scheduled pushes)
SLOT_CONFIGS = {
    1: {
        "id": 1,
        "name": "morning",
        "title": "🌅 Morning Fundamentals",
        "theme": "Core Fundamentals & Language Internals",
        "start_hour": 4,
        "end_hour": 11,
        "description": "Essential architecture, runtime lifecycles, and core language concepts.",
    },
    2: {
        "id": 2,
        "name": "afternoon",
        "title": "☀️ Afternoon Architecture",
        "theme": "Architecture, Coding Patterns & System Design",
        "start_hour": 11,
        "end_hour": 17,
        "description": "Scalable design patterns, database query performance, and algorithmic challenges.",
    },
    3: {
        "id": 3,
        "name": "evening",
        "title": "🌙 Evening Scenarios",
        "theme": "Real-World Scenarios, Company Specifics & Behavioral",
        "start_hour": 17,
        "end_hour": 24,
        "description": "Production edge-cases, incident debugging, and company interview insights.",
    },
}

# Number of questions generated per slot
QUESTIONS_PER_SLOT = 5

# Safety Guard Filters
MIN_REPO_STARS = 50
MAX_CONTENT_BYTES = 500_000  # 500 KB per source doc to prevent buffer bloat
ALLOWED_FILE_EXTENSIONS = {".md", ".markdown", ".txt", ".json", ".rst"}
BLOCKED_EXTENSIONS = {".sh", ".exe", ".bin", ".py", ".js", ".ts", ".apk", ".deb", ".tar", ".gz", ".zip"}

# Reputable Curated Repositories for Tech Stack Matching
TRUSTED_CURATED_REPOS = [
    {
        "name": "yangshun/tech-interview-handbook",
        "url": "https://github.com/yangshun/tech-interview-handbook",
        "raw_base": "https://raw.githubusercontent.com/yangshun/tech-interview-handbook/master",
        "stars": 112000,
        "tags": ["algorithms", "fullstack", "system-design", "general", "javascript"],
    },
    {
        "name": "donnemartin/system-design-primer",
        "url": "https://github.com/donnemartin/system-design-primer",
        "raw_base": "https://raw.githubusercontent.com/donnemartin/system-design-primer/master",
        "stars": 280000,
        "tags": ["system-design", "backend", "architecture", "scalability", "python"],
    },
    {
        "name": "yangshun/front-end-interview-handbook",
        "url": "https://github.com/yangshun/front-end-interview-handbook",
        "raw_base": "https://raw.githubusercontent.com/yangshun/front-end-interview-handbook/master",
        "stars": 42000,
        "tags": ["frontend", "javascript", "react", "html", "css", "web"],
    },
    {
        "name": "Sudheerr/ReactJS-Interview-Questions",
        "url": "https://github.com/Sudheerr/ReactJS-Interview-Questions",
        "raw_base": "https://raw.githubusercontent.com/Sudheerr/ReactJS-Interview-Questions/master",
        "stars": 33000,
        "tags": ["react", "frontend", "javascript", "mern", "fullstack"],
    },
    {
        "name": "alexey-pelykh/flutter-interview-questions",
        "url": "https://github.com/alexey-pelykh/flutter-interview-questions",
        "raw_base": "https://raw.githubusercontent.com/alexey-pelykh/flutter-interview-questions/master",
        "stars": 2800,
        "tags": ["flutter", "dart", "mobile", "frontend"],
    },
    {
        "name": "kdn251/interviews",
        "url": "https://github.com/kdn251/interviews",
        "raw_base": "https://raw.githubusercontent.com/kdn251/interviews/master",
        "stars": 62000,
        "tags": ["algorithms", "datastructures", "fullstack", "java", "python"],
    },
    {
        "name": "learning-zone/python-interview-questions",
        "url": "https://github.com/learning-zone/python-interview-questions",
        "raw_base": "https://raw.githubusercontent.com/learning-zone/python-interview-questions/master",
        "stars": 5400,
        "tags": ["python", "backend", "django", "fastapi", "fullstack"],
    },
    {
        "name": "DopplerHQ/awesome-interview-questions",
        "url": "https://github.com/DopplerHQ/awesome-interview-questions",
        "raw_base": "https://raw.githubusercontent.com/DopplerHQ/awesome-interview-questions/master",
        "stars": 65000,
        "tags": ["general", "fullstack", "devops", "qa", "testing", "mobile"],
    },
]

# Trusted Tech Communities and Social Media Handles
TRUSTED_SOCIAL_HANDLES = [
    {
        "platform": "LeetCode Discuss",
        "handle": "@LeetCodeExperience",
        "url": "https://leetcode.com/discuss/interview-experience",
        "type": "interview_digest",
        "reliability_score": 0.98,
        "tags": ["algorithms", "faang", "product-based", "system-design"],
    },
    {
        "platform": "Reddit r/cscareerquestions",
        "handle": "r/cscareerquestions",
        "url": "https://reddit.com/r/cscareerquestions",
        "type": "community_archive",
        "reliability_score": 0.92,
        "tags": ["career", "behavioral", "negotiation", "questions"],
    },
    {
        "platform": "Engineering Blogs Digest",
        "handle": "@TechEngBlogs",
        "url": "https://github.com/kilimchoi/engineering-blogs",
        "type": "engineering_insights",
        "reliability_score": 0.96,
        "tags": ["architecture", "scale", "netflix", "uber", "meta"],
    },
    {
        "platform": "Glassdoor Interview Reports",
        "handle": "Glassdoor Tech Archive",
        "url": "https://glassdoor.com/Interview",
        "type": "company_specific",
        "reliability_score": 0.91,
        "tags": ["company", "salary", "culture", "rounds"],
    },
]
