import json
from focus_goblin.storage import Store
from focus_goblin.engine import Settings


def test_roundtrip_and_demo_exclusion(tmp_path):
    s = Store(tmp_path/'test.sqlite3')
    s.save_settings(Settings(calibrated=True,baseline=(.1,.2,.4,.6)))
    assert s.load_settings().baseline == [.1,.2,.4,.6]
    demo = s.start('Study',True); s.checkpoint(demo,{'focus':999},True)
    real = s.start('Work'); s.event(real,'state','focused'); s.sample(real,1,.8,'focused')
    s.checkpoint(real,{'focus':60},True)
    assert len(s.daily()) == 7 and s.daily()[-1][1] == 60
    assert len(s.history()) == 2
    out = tmp_path/'export.csv'; s.export(out)
    assert 'summary_json' in out.read_text(encoding='utf-8-sig')
    assert not any('frame' in name for (name,) in s.db.execute("SELECT name FROM sqlite_master WHERE type='table'"))
    s.close()


def test_interrupted_session_retains_checkpoint_and_is_marked(tmp_path):
    path = tmp_path/'interrupted.sqlite3'
    first = Store(path)
    sid = first.start('Study')
    first.checkpoint(sid,{'focus':42})
    first.close()
    recovered = Store(path)
    ended,payload = recovered.db.execute('SELECT ended,summary FROM sessions WHERE id=?',(sid,)).fetchone()
    assert ended and json.loads(payload)['focus'] == 42
    assert recovered.db.execute("SELECT COUNT(*) FROM events WHERE kind='interrupted'").fetchone()[0] == 1
    recovered.close()
