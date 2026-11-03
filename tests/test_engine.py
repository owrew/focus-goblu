import pytest
from focus_goblin.engine import AttentionEngine, Observation, Settings


def engine(**kwargs):
    return AttentionEngine(Settings(calibrated=True,**kwargs))


def run(e,obs,seconds):
    for _ in range(int(seconds*10)):
        d = e.step(obs,.1)
    return d


def test_short_glance_does_not_trigger_and_refocus_clears_episode():
    e = engine()
    assert run(e,Observation(True,yaw=.4),2).state == "watching"
    assert e.alerts == e.distractions == 0
    assert run(e,Observation(True),2).state == "focused"
    assert e.away == 0


def test_phone_without_looking_away_never_triggers():
    e = engine()
    assert run(e,Observation(True,phone=True),30).state == "focused"
    assert e.alerts == 0 and e.phone_events == 1


def test_phone_downward_accelerates_and_cooldown_works():
    e = engine()
    run(e,Observation(True,pitch=.4,phone=True),6)
    assert e.alerts == 1 and e.distractions == 1
    run(e,Observation(True,pitch=.4,phone=True),10)
    assert e.alerts == 1
    run(e,Observation(True,pitch=.4,phone=True),12)
    assert e.alerts == 2 and e.distractions == 1


def test_unknown_absent_and_uncalibrated_not_focus():
    e = engine()
    run(e,Observation(valid=False),5)
    run(e,Observation(face=False),5)
    assert e.focus == e.distracted == e.alerts == 0
    assert e.unknown == pytest.approx(5) and e.absent == pytest.approx(5)
    e.settings.calibrated = False
    run(e,Observation(True),5)
    assert e.focus == 0


def test_break_timer_and_accounting():
    e = engine(break_minutes=1)
    run(e,Observation(True),61)
    assert e.break_due()
    s = e.summary()
    assert s['active'] == pytest.approx(s['focus']+s['distracted']+s['unknown']+s['absent'])
    e.take_break()
    assert not e.break_due() and e.streak == 0


def test_paper_mode_still_reacts_to_phone():
    e = engine(paper_mode=True)
    assert run(e,Observation(True,pitch=.4),10).state == 'focused'
    assert run(e,Observation(True,pitch=.4,phone=True),10).state == 'angry'


def test_stalled_dt_is_bounded():
    e = engine()
    e.step(Observation(True),20)
    assert e.focus == .5


def test_recovery_hysteresis_and_blink():
    e = engine()
    run(e,Observation(True,yaw=.4),9)
    assert run(e,Observation(True),.5).state == 'calming'
    assert run(e,Observation(True),2).state == 'focused'
    assert run(e,Observation(True,gaze_y=2,eyes_open=False),10).state == 'focused'
