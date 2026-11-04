"""Only settings, aggregated durations, sampled scores and events are persisted."""
import csv
import json
import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import asdict
from .engine import Settings


def data_dir():
    path = Path(os.getenv("LOCALAPPDATA", str(Path.home()/".local"/"share"))) / "FocusGoblin"
    path.mkdir(parents=True, exist_ok=True)
    return path


class Store:
    def __init__(self, path=None):
        self.db = sqlite3.connect(path or data_dir()/"focus.sqlite3")
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript('''
          CREATE TABLE IF NOT EXISTS settings(id INTEGER PRIMARY KEY CHECK(id=1), payload TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS sessions(id INTEGER PRIMARY KEY, started TEXT NOT NULL,
            ended TEXT, mode TEXT NOT NULL, demo INTEGER NOT NULL DEFAULT 0, summary TEXT NOT NULL DEFAULT '{}');
          CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY, session_id INTEGER NOT NULL,
            at TEXT NOT NULL, kind TEXT NOT NULL, detail TEXT NOT NULL,
            FOREIGN KEY(session_id) REFERENCES sessions(id));
          CREATE TABLE IF NOT EXISTS samples(id INTEGER PRIMARY KEY, session_id INTEGER NOT NULL,
            elapsed REAL NOT NULL, confidence REAL NOT NULL, state TEXT NOT NULL,
            FOREIGN KEY(session_id) REFERENCES sessions(id));
          CREATE TABLE IF NOT EXISTS session_plans(session_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL, duration_seconds INTEGER NOT NULL, tasks_json TEXT NOT NULL,
            FOREIGN KEY(session_id) REFERENCES sessions(id));
        ''')
        # A process exit leaves an honest interrupted session, with latest checkpoint.
        interrupted = self.db.execute("SELECT id FROM sessions WHERE ended IS NULL").fetchall()
        for (sid,) in interrupted:
            self.event(sid,"interrupted","Previous process ended without a clean session stop; summary is last checkpoint")
        self.db.execute("UPDATE sessions SET ended=? WHERE ended IS NULL", (datetime.now().astimezone().isoformat(),))
        self.db.commit()

    def load_settings(self):
        row = self.db.execute("SELECT payload FROM settings WHERE id=1").fetchone()
        try:
            if not row:return Settings()
            payload=json.loads(row[0])
            if 'phone_backend' not in payload:payload['phone_confidence']=min(.25,float(payload.get('phone_confidence',.25)))
            return Settings(**payload).validated()
        except (TypeError, ValueError, json.JSONDecodeError):
            return Settings()

    def save_settings(self, s):
        self.db.execute("INSERT OR REPLACE INTO settings VALUES(1,?)", (json.dumps(asdict(s)),))
        self.db.commit()

    def start(self, mode, demo=False):
        cur = self.db.execute("INSERT INTO sessions(started,mode,demo) VALUES(?,?,?)", (datetime.now().astimezone().isoformat(), mode, int(demo)))
        self.db.commit()
        return cur.lastrowid

    def event(self, sid, kind, detail):
        self.db.execute("INSERT INTO events(session_id,at,kind,detail) VALUES(?,?,?,?)", (sid, datetime.now().astimezone().isoformat(), kind, detail))
        self.db.commit()

    def sample(self, sid, elapsed, confidence, state):
        self.db.execute("INSERT INTO samples(session_id,elapsed,confidence,state) VALUES(?,?,?,?)", (sid, elapsed, confidence, state))

    def checkpoint(self, sid, summary, end=False):
        self.db.execute("UPDATE sessions SET summary=? WHERE id=?", (json.dumps(summary), sid))
        if end:
            self.db.execute("UPDATE sessions SET ended=? WHERE id=?", (datetime.now().astimezone().isoformat(), sid))
        self.db.commit()

    def history(self):
        return self.db.execute("SELECT id,started,mode,demo,summary FROM sessions ORDER BY id DESC LIMIT 100").fetchall()

    def daily(self):
        return self.daily_range(7)

    def daily_range(self,count=7):
        days = {}
        for started, payload in self.db.execute("SELECT started,summary FROM sessions WHERE demo=0 ORDER BY started"):
            day = started[:10]
            days[day] = days.get(day, 0) + json.loads(payload).get("focus", 0)
        today = datetime.now().date()
        count = max(1,min(366,int(count)))
        return [((today-timedelta(days=i)).isoformat(),days.get((today-timedelta(days=i)).isoformat(),0)) for i in range(count-1,-1,-1)]

    def comparison(self, days, today=None):
        today = today or datetime.now().date()
        start = today - timedelta(days=days-1)
        prior = start - timedelta(days=days)
        periods = []
        for low,high in ((start,today),(prior,start-timedelta(days=1))):
            totals = dict.fromkeys(('focus','distracted','unknown','absent','alerts','sessions'),0)
            for (payload,) in self.db.execute(
                "SELECT summary FROM sessions WHERE demo=0 AND started>=? AND started<?",
                (low.isoformat(),(high+timedelta(days=1)).isoformat()),
            ):
                summary = json.loads(payload)
                for key in ('focus','distracted','unknown','absent','alerts'):
                    totals[key] += summary.get(key,0)
                totals['sessions'] += 1
            totals['range'] = f'{low:%Y-%m-%d} to {high:%Y-%m-%d}'
            periods.append(totals)
        return periods

    def save_plan(self,sid,name,duration,tasks):
        self.db.execute('INSERT OR REPLACE INTO session_plans VALUES(?,?,?,?)',(sid,name,int(duration),json.dumps(tasks)))
        self.db.commit()

    def plan(self,sid):
        row = self.db.execute('SELECT name,duration_seconds,tasks_json FROM session_plans WHERE session_id=?',(sid,)).fetchone()
        return (row[0],row[1],json.loads(row[2])) if row else ('Unplanned',0,[])

    def events_for(self,sid):
        return self.db.execute('SELECT at,kind,detail FROM events WHERE session_id=? ORDER BY id DESC LIMIT 200',(sid,)).fetchall()

    def backup(self,path):
        target = sqlite3.connect(path)
        try: self.db.backup(target)
        finally: target.close()

    def delete_sessions(self,ids):
        with self.db:
            for sid in ids:
                for table in ('samples','events','session_plans'):
                    self.db.execute(f'DELETE FROM {table} WHERE session_id=?',(int(sid),))
                self.db.execute('DELETE FROM sessions WHERE id=?',(int(sid),))

    def prune(self,days,exclude=None):
        if int(days) <= 0: return 0
        cutoff = (datetime.now()-timedelta(days=int(days))).date().isoformat()
        ids = [r[0] for r in self.db.execute('SELECT id FROM sessions WHERE ended IS NOT NULL AND started<?',(cutoff,)) if r[0] != exclude]
        if ids:
            self.backup(data_dir()/f'before-retention-{datetime.now():%Y%m%d-%H%M%S}.sqlite3')
            self.delete_sessions(ids)
        return len(ids)

    def export_all(self,path):
        data = {}
        for table in ('sessions','session_plans','events','samples'):
            cursor = self.db.execute(f'SELECT * FROM {table}')
            names = [col[0] for col in cursor.description]
            data[table] = [dict(zip(names,row)) for row in cursor]
        Path(path).write_text(json.dumps(data,indent=2),encoding='utf-8')

    def export(self, path):
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["id", "started", "mode", "demo", "summary_json"])
            w.writerows(self.history())

    def close(self):
        self.db.close()
