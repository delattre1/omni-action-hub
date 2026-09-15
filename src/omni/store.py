import os
import sqlite3
import tempfile
import time
import uuid
from pathlib import Path


class Store:
    """One durable queue and usage ledger per installation; one worker process."""
    def __init__(self, root: Path):
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.root = root
        self.images = root / "images"
        self.downloads = root / "downloads"
        for directory in (root, self.images, self.downloads):
            if directory.is_symlink():
                raise ValueError("unsafe data directory")
            directory.mkdir(exist_ok=True, mode=0o700)
            if directory.stat().st_uid == os.geteuid():
                directory.chmod(0o700)
        if (root / "state.db").is_symlink():
            raise ValueError("unsafe database path")
        self.db = sqlite3.connect(root / "state.db", timeout=15)
        os.chmod(root / "state.db", 0o600)
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
        PRAGMA journal_mode=WAL;
        PRAGMA secure_delete=ON;
        CREATE TABLE IF NOT EXISTS jobs (
          id TEXT PRIMARY KEY, chat TEXT NOT NULL, message TEXT NOT NULL,
          text TEXT NOT NULL, image TEXT, mime TEXT, state TEXT NOT NULL,
          report TEXT, asset TEXT, ticket TEXT, reply TEXT, delivery TEXT DEFAULT 'pending',
          attempts INTEGER DEFAULT 0, created REAL NOT NULL, updated REAL NOT NULL,
          UNIQUE(chat,message));
        CREATE TABLE IF NOT EXISTS usage_calls (id TEXT PRIMARY KEY, recorded REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS session_model_usage (
          session_id TEXT PRIMARY KEY, model TEXT NOT NULL, billing_provider TEXT,
          task TEXT, input_tokens INTEGER NOT NULL, output_tokens INTEGER NOT NULL,
          cache_read_tokens INTEGER NOT NULL, cache_write_tokens INTEGER NOT NULL,
          first_seen REAL NOT NULL, last_seen REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS inbound_images (
          chat TEXT NOT NULL, sender TEXT NOT NULL, message TEXT NOT NULL,
          guid TEXT, image BLOB, mime TEXT, created REAL NOT NULL,
          PRIMARY KEY(chat,sender,message));
        CREATE TABLE IF NOT EXISTS notices (
          job TEXT NOT NULL REFERENCES jobs(id), kind TEXT NOT NULL,
          status TEXT NOT NULL, updated REAL NOT NULL, PRIMARY KEY(job,kind));
        CREATE TABLE IF NOT EXISTS provisioning (
          name TEXT PRIMARY KEY, operation_id TEXT NOT NULL, created REAL NOT NULL);
        PRAGMA user_version=4;
        """)

        columns = {row[1] for row in self.db.execute("PRAGMA table_info(jobs)")}
        for name, kind in (("wait_sender", "TEXT"), ("wait_reference", "TEXT"), ("deadline", "REAL")):
            if name not in columns:
                self.db.execute(f"ALTER TABLE jobs ADD COLUMN {name} {kind}")
        self.db.commit()

    def claim_provision(self, name):
        operation = str(uuid.uuid4())
        with self.db:
            claimed = self.db.execute("INSERT OR IGNORE INTO provisioning VALUES(?,?,?)",
                                      (name, operation, time.time())).rowcount
        return operation if claimed else None

    def claim_notice(self, job, kind):
        with self.db:
            return bool(self.db.execute("INSERT OR IGNORE INTO notices VALUES(?,?,?,?)",
                                       (job, kind, "attempted", time.time())).rowcount)

    def finish_notice(self, job, kind, success):
        with self.db:
            self.db.execute("UPDATE notices SET status=?,updated=? WHERE job=? AND kind=?",
                            ("sent" if success else "unconfirmed", time.time(), job, kind))

    def check_downloads(self):
        # Executed by the actual gateway UID, never inferred from a root doctor.
        with tempfile.TemporaryFile(dir=self.downloads) as probe:
            probe.write(b"omni-cache-probe")
            probe.flush()

    def close(self):
        self.db.close()

    def get(self, job_id):
        row = self.db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        return dict(row) if row else None

    def lookup(self, chat, message):
        row = self.db.execute("SELECT * FROM jobs WHERE chat=? AND message=?", (chat, message)).fetchone()
        return dict(row) if row else None

    def enqueue(self, chat, message, text, image=None, mime=None, reply=None, sources=(), wait_sender=None, wait_reference=None):
        previous = self.lookup(chat, message)
        if previous:
            return previous["id"]
        job_id = str(uuid.uuid4())
        target = None
        if image is not None:
            target = str(self.images / job_id)
            fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "wb") as f:
                f.write(image)
                f.flush()
                os.fsync(f.fileno())
        now = time.time()
        with self.db:
            self.db.execute("INSERT INTO jobs(id,chat,message,text,image,mime,state,reply,created,updated) VALUES(?,?,?,?,?,?,?,?,?,?)",
                            (job_id, chat, message, text, target, mime, "ready" if reply else "queued", reply, now, now))
            if wait_sender:
                self.db.execute("UPDATE jobs SET state='waiting',wait_sender=?,wait_reference=?,deadline=? WHERE id=?",
                                (wait_sender, wait_reference, now + 60, job_id))
            for source in sources:
                self.db.execute("UPDATE inbound_images SET image=NULL WHERE chat=? AND sender=? AND message=?",
                                (source["chat"], source["sender"], source["message"]))
        return job_id

    def buffer_image(self, chat, sender, message, guid, image, mime):
        total = self.db.execute("SELECT coalesce(sum(length(image)),0) FROM inbound_images").fetchone()[0]
        if total + len(image or b"") > 100 * 1024 * 1024:
            raise ValueError("buffer capacity exceeded")
        with self.db:
            self.db.execute("INSERT OR IGNORE INTO inbound_images VALUES(?,?,?,?,?,?,?)",
                            (chat, sender, message, guid, image, mime, time.time()))

    def buffered(self, chat, sender, reference=None):
        cutoff = time.time() - (86400 if reference else 60)
        query = "SELECT * FROM inbound_images WHERE chat=? AND sender=? AND image IS NOT NULL AND created>=?"
        args = [chat, sender, cutoff]
        if reference:
            query += " AND (message=? OR guid=?)"
            args += [reference, reference]
        return [dict(row) for row in self.db.execute(query, args)]

    def waiting(self, chat, sender):
        return [dict(row) for row in self.db.execute(
            "SELECT * FROM jobs WHERE state='waiting' AND chat=? AND wait_sender=? AND deadline>=? ORDER BY created",
            (chat, sender, time.time()))]

    def attach_waiting(self, job, source):
        fd, target = tempfile.mkstemp(prefix="job-", dir=self.images)
        with os.fdopen(fd, "wb") as out:
            out.write(source["image"])
            out.flush()
            os.fsync(out.fileno())
        with self.db:
            self.db.execute("UPDATE jobs SET image=?,mime=?,state='queued',updated=? WHERE id=? AND state='waiting'",
                            (target, source["mime"], time.time(), job["id"]))
            self.db.execute("UPDATE inbound_images SET image=NULL WHERE chat=? AND sender=? AND message=?",
                            (source["chat"], source["sender"], source["message"]))

    def update(self, job_id, **fields):
        allowed = {"state", "report", "asset", "ticket", "reply", "delivery", "attempts", "image", "text"}
        if not fields or not fields.keys() <= allowed:
            raise ValueError("invalid state update")
        fields["updated"] = time.time()
        with self.db:
            self.db.execute(f"UPDATE jobs SET {','.join(k+'=?' for k in fields)} WHERE id=?",
                            (*fields.values(), job_id))

    def pending(self):
        return [dict(r) for r in self.db.execute(
            "SELECT * FROM jobs WHERE state NOT IN ('done','held') AND delivery != 'paused' ORDER BY created")]

    def cleanup_image(self, job):
        if job["image"]:
            p = Path(job["image"])
            if p.parent.resolve() == self.images.resolve():
                p.unlink(missing_ok=True)
        self.update(job["id"], image=None, text="")

    def expire_images(self):
        cutoff = time.time() - 86400
        with self.db:
            self.db.execute("UPDATE inbound_images SET image=NULL WHERE created<? AND image IS NOT NULL", (cutoff,))
        for p in (*self.images.iterdir(), *self.downloads.iterdir()):
            if p.is_file() and p.stat().st_mtime < cutoff:
                p.unlink(missing_ok=True)

    def usage(self, call_id, model, usage):
        """Persist only provider-reported counts, once per actual API response.

        Expose the official collector's documented session_model_usage contract
        in this dedicated store; do not alter Hermes' own state.db.
        """
        prompt = int(usage.get("promptTokenCount", 0))
        cached = int(usage.get("cachedContentTokenCount", 0))
        output = int(usage.get("candidatesTokenCount", 0)) + int(usage.get("thoughtsTokenCount", 0))
        if min(prompt, cached, output) < 0 or cached > prompt:
            raise ValueError("invalid usage")
        now = time.time()
        with self.db:
            inserted = self.db.execute("INSERT OR IGNORE INTO usage_calls VALUES(?,?)", (call_id, now)).rowcount
            if inserted:
                self.db.execute("INSERT INTO session_model_usage VALUES(?,?,?,?,?,?,?,?,?,?)",
                                (call_id, model, "google", "omni_vision", prompt-cached, output, cached, 0, now, now))

    def retry_delivery(self, job_id):
        job = self.get(job_id)
        if not job or not job["reply"]:
            raise ValueError("no saved reply")
        state = "unknown" if not job["ticket"] and job["state"] in ("held", "unknown") else "ready"
        self.update(job_id, state=state, delivery="pending", attempts=0)
