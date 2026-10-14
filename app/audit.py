"""Append-only, tamper-evident audit log (SQLite + hash chain).

Each record stores the hash of the previous one, so editing or deleting any past
decision breaks the chain and `verify_chain()` reports it. The raw video is never
stored — only its SHA-256 — which keeps personal data out of the log.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
from pathlib import Path

from .schemas import AuditRecord

GENESIS = "0" * 64
_lock = threading.Lock()


class AuditLog:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(path), check_same_thread=False)
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS decisions (
                seq INTEGER PRIMARY KEY AUTOINCREMENT,
                decision_id TEXT UNIQUE NOT NULL,
                payload TEXT NOT NULL,
                prev_hash TEXT NOT NULL,
                record_hash TEXT NOT NULL)"""
        )
        self.conn.commit()

    @staticmethod
    def _hash(payload: str, prev_hash: str) -> str:
        return hashlib.sha256((prev_hash + payload).encode()).hexdigest()

    def _last_hash(self) -> str:
        row = self.conn.execute("SELECT record_hash FROM decisions ORDER BY seq DESC LIMIT 1").fetchone()
        return row[0] if row else GENESIS

    def append(self, data: dict) -> AuditRecord:
        with _lock:
            prev = self._last_hash()
            payload = json.dumps(data, sort_keys=True, default=str)
            h = self._hash(payload, prev)
            self.conn.execute(
                "INSERT INTO decisions (decision_id, payload, prev_hash, record_hash) VALUES (?,?,?,?)",
                (data["decision_id"], payload, prev, h),
            )
            self.conn.commit()
        return AuditRecord(**data, prev_hash=prev, record_hash=h)

    def get(self, decision_id: str) -> AuditRecord | None:
        row = self.conn.execute(
            "SELECT payload, prev_hash, record_hash FROM decisions WHERE decision_id=?", (decision_id,)
        ).fetchone()
        if not row:
            return None
        return AuditRecord(**json.loads(row[0]), prev_hash=row[1], record_hash=row[2])

    def verify_chain(self) -> tuple[bool, int, int | None]:
        """Returns (ok, records_checked, first_bad_seq)."""
        prev = GENESIS
        n = 0
        for seq, payload, prev_hash, record_hash in self.conn.execute(
            "SELECT seq, payload, prev_hash, record_hash FROM decisions ORDER BY seq"
        ):
            n += 1
            if prev_hash != prev or self._hash(payload, prev) != record_hash:
                return False, n, seq
            prev = record_hash
        return True, n, None
