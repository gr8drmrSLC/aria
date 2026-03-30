"""
ARIA SQLite Store Module
------------------------
This module provides a data access layer for ARIA, managing persistent 
storage for papers, reports, and baseline statistics in a SQLite database.
"""

import os
import sqlite3
import json
import logging
from datetime import datetime, timezone, timedelta

# Module logger
logger = logging.getLogger('aria.store')

class Database:
    """
    Handles connections and operations for the ARIA SQLite database.
    Supports context manager usage for automatic connection management.
    """

    def __init__(self, db_path=None):
        self.db_path = db_path or os.environ.get('ARIA_DB_PATH', 'data/aria.db')
        self.conn = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def connect(self):
        """Establishes a connection to the SQLite database and sets the row factory."""
        if not self.conn:
            db_dir = os.path.dirname(self.db_path)
            if db_dir:
                os.makedirs(db_dir, exist_ok=True)
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
            logger.debug(f"Connected to database at {self.db_path}")

    def close(self):
        """Closes the active database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
            logger.debug("Database connection closed")

    def init_db(self):
        """Creates the necessary tables if they do not exist."""
        self.connect()
        cursor = self.conn.cursor()

        # Papers table: stores metadata and analysis results
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS papers (
                id TEXT PRIMARY KEY,
                title TEXT,
                abstract TEXT,
                authors TEXT,
                categories TEXT,
                published TEXT,
                novelty_score REAL DEFAULT 0,
                themes TEXT,
                ingested_at TEXT
            )
        ''')

        # Reports table: stores generated summaries and analytics reports
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                content TEXT,
                triggers TEXT,
                paper_count INTEGER,
                created_at TEXT
            )
        ''')

        # Baselines table: stores daily aggregate statistics per category
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS baselines (
                category TEXT,
                date TEXT,
                paper_count INTEGER,
                avg_novelty REAL,
                PRIMARY KEY (category, date)
            )
        ''')

        self.conn.commit()
        logger.info("Database initialized successfully")

    def save_papers(self, papers: list[dict]):
        """Upserts a list of papers with current UTC timestamp for ingestion."""
        self.connect()
        cursor = self.conn.cursor()
        now = datetime.now(timezone.utc).isoformat()

        for paper in papers:
            cursor.execute('''
                INSERT INTO papers (
                    id, title, abstract, authors, categories, published, ingested_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    title=excluded.title,
                    abstract=excluded.abstract,
                    authors=excluded.authors,
                    categories=excluded.categories,
                    published=excluded.published
            ''', (
                paper['id'],
                paper['title'],
                paper['abstract'],
                json.dumps(paper.get('authors', [])),
                json.dumps(paper.get('categories', [])),
                paper['published'],
                now
            ))
        
        self.conn.commit()
        logger.debug(f"Saved {len(papers)} papers")

    def update_analysis(self, paper_id: str, novelty_score: float, themes: list[str]):
        """Updates the novelty score and themes for a specific paper."""
        self.connect()
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE papers 
            SET novelty_score = ?, themes = ? 
            WHERE id = ?
        ''', (novelty_score, json.dumps(themes), paper_id))
        self.conn.commit()

    def save_report(self, title: str, content: str, triggers: list[str], paper_count: int) -> int:
        """Saves a report and returns its unique database ID."""
        self.connect()
        cursor = self.conn.cursor()
        now = datetime.now(timezone.utc).isoformat()
        
        cursor.execute('''
            INSERT INTO reports (title, content, triggers, paper_count, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (title, content, json.dumps(triggers), paper_count, now))
        
        report_id = cursor.lastrowid
        self.conn.commit()
        return report_id

    def get_recent_papers(self, hours=24) -> list[dict]:
        """Retrieves papers ingested within the specified time window."""
        self.connect()
        cursor = self.conn.cursor()
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
        
        cursor.execute('SELECT * FROM papers WHERE ingested_at >= ?', (cutoff,))
        rows = cursor.fetchall()
        
        papers = []
        for row in rows:
            p = dict(row)
            p['authors'] = json.loads(p['authors']) if p['authors'] else []
            p['categories'] = json.loads(p['categories']) if p['categories'] else []
            p['themes'] = json.loads(p['themes']) if p['themes'] else []
            papers.append(p)
        return papers

    def get_reports(self, limit=20) -> list[dict]:
        """Retrieves the most recent reports up to the specified limit."""
        self.connect()
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM reports ORDER BY created_at DESC LIMIT ?', (limit,))
        
        reports = []
        for row in cursor.fetchall():
            r = dict(row)
            r['triggers'] = json.loads(r['triggers']) if r['triggers'] else []
            reports.append(r)
        return reports

    def get_report(self, report_id: int) -> dict|None:
        """Retrieves a single report by its ID."""
        self.connect()
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM reports WHERE id = ?', (report_id,))
        row = cursor.fetchone()
        
        if row:
            r = dict(row)
            r['triggers'] = json.loads(r['triggers']) if r['triggers'] else []
            return r
        return None

    def update_baseline(self, category: str, date: str, paper_count: int, avg_novelty: float):
        """Upserts baseline statistics for a given category and date."""
        self.connect()
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO baselines (category, date, paper_count, avg_novelty)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(category, date) DO UPDATE SET
                paper_count = excluded.paper_count,
                avg_novelty = excluded.avg_novelty
        ''', (category, date, paper_count, avg_novelty))
        self.conn.commit()

    def get_baselines(self, category: str, days=30) -> list[dict]:
        """Retrieves baseline history for a category over a range of days."""
        self.connect()
        cursor = self.conn.cursor()
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime('%Y-%m-%d')
        
        cursor.execute('''
            SELECT * FROM baselines 
            WHERE category = ? AND date >= ? 
            ORDER BY date ASC
        ''', (category, cutoff))
        
        return [dict(row) for row in cursor.fetchall()]

    def get_paper_count_today(self) -> int:
        """Counts papers published on the current date."""
        self.connect()
        cursor = self.conn.cursor()
        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        cursor.execute("SELECT COUNT(*) FROM papers WHERE published LIKE ?", (f"{today}%",))
        result = cursor.fetchone()
        return result[0] if result else 0
