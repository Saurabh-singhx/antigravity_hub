"""SQLite Database Schemas and Migration DDL."""

SCHEMA_STATEMENTS = [
    # 1. Historical Notifications & Actions
    """
    CREATE TABLE IF NOT EXISTS notifications (
        id TEXT PRIMARY KEY,
        workflow TEXT NOT NULL,
        title TEXT NOT NULL,
        message TEXT NOT NULL,
        level TEXT NOT NULL,
        category TEXT NOT NULL,
        action_id TEXT,
        action_type TEXT,
        action_prompt TEXT,
        action_options TEXT,
        action_status TEXT,
        action_response TEXT,
        screenshot_url TEXT,
        metadata_json TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_workflow_created 
    ON notifications(workflow, created_at DESC)
    """,

    # 2. Registered Devices & Push Tokens
    """
    CREATE TABLE IF NOT EXISTS device_tokens (
        device_id TEXT PRIMARY KEY,
        device_name TEXT,
        push_token TEXT,
        platform TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,

    # 3. Verified Interview Questions & Answers
    """
    CREATE TABLE IF NOT EXISTS qna_questions (
        id TEXT PRIMARY KEY,
        job_title TEXT NOT NULL,
        company TEXT,
        slot_id INTEGER NOT NULL,
        slot_name TEXT NOT NULL,
        date TEXT NOT NULL,
        question TEXT NOT NULL,
        answer TEXT NOT NULL,
        category TEXT DEFAULT 'Fundamentals',
        tech_stack_json TEXT,
        source_type TEXT DEFAULT 'github_repo',
        source_name TEXT NOT NULL,
        source_url TEXT NOT NULL,
        source_quote TEXT,
        source_stars INTEGER DEFAULT 0,
        reliability_score REAL DEFAULT 1.0,
        verified INTEGER DEFAULT 1,
        difficulty TEXT DEFAULT 'Medium',
        is_mastered INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_qna_date_slot 
    ON qna_questions(date, slot_id, created_at DESC)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_qna_job_title 
    ON qna_questions(job_title)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_qna_created 
    ON qna_questions(created_at DESC)
    """,

    # 4. Slot Execution Tracker (strictly limits to 3 times a day, records skips)
    """
    CREATE TABLE IF NOT EXISTS qna_slot_executions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        slot_id INTEGER NOT NULL,
        slot_name TEXT NOT NULL,
        executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        question_count INTEGER DEFAULT 0,
        status TEXT NOT NULL,
        notes TEXT,
        UNIQUE(date, slot_id)
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_slot_date 
    ON qna_slot_executions(date, slot_id)
    """
]
