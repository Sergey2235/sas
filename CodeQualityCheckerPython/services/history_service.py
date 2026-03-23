"""
History Service - SQLite storage for analysis history.
"""
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass
class AnalysisRecord:
    id: int
    code: str
    language: str
    result: str
    timestamp: datetime
    analysis_type: str
    source: str


class HistoryService:
    def __init__(self, db_path: str = "analysis_history.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS analysis_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL,
                language TEXT NOT NULL,
                result TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                analysis_type TEXT DEFAULT 'Full',
                source TEXT DEFAULT 'local'
            )
            """
        )
        conn.commit()
        conn.close()

    async def save_analysis(
        self,
        code: str,
        language: str,
        result: str,
        analysis_type: str = "Full",
        source: str = "local",
    ) -> int:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO analysis_history (code, language, result, analysis_type, source)
            VALUES (?, ?, ?, ?, ?)
            """,
            (code, language, result, analysis_type, source),
        )
        analysis_id = int(cursor.lastrowid)
        conn.commit()
        conn.close()
        return analysis_id

    async def get_history(self, limit: int = 50) -> List[AnalysisRecord]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, code, language, result, timestamp, analysis_type, source
            FROM analysis_history
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = cursor.fetchall()
        conn.close()
        return [self._row_to_record(row) for row in rows]

    async def get_analysis(self, analysis_id: int) -> Optional[AnalysisRecord]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, code, language, result, timestamp, analysis_type, source
            FROM analysis_history
            WHERE id = ?
            """,
            (analysis_id,),
        )
        row = cursor.fetchone()
        conn.close()
        return self._row_to_record(row) if row else None

    async def delete_analysis(self, analysis_id: int) -> bool:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM analysis_history WHERE id = ?", (analysis_id,))
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return deleted

    async def clear_history(self) -> int:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM analysis_history")
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        return deleted

    async def search_history(self, query: str, limit: int = 20) -> List[AnalysisRecord]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        wildcard = f"%{query}%"
        cursor.execute(
            """
            SELECT id, code, language, result, timestamp, analysis_type, source
            FROM analysis_history
            WHERE code LIKE ? OR language LIKE ?
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (wildcard, wildcard, limit),
        )
        rows = cursor.fetchall()
        conn.close()
        return [self._row_to_record(row) for row in rows]

    def _row_to_record(self, row: sqlite3.Row) -> AnalysisRecord:
        timestamp = row["timestamp"]
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        return AnalysisRecord(
            id=row["id"],
            code=row["code"],
            language=row["language"],
            result=row["result"],
            timestamp=timestamp,
            analysis_type=row["analysis_type"],
            source=row["source"],
        )
