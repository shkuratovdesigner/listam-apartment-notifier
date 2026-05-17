from listam_notifier.state import load_state, save_state, State


def test_load_state_missing_file_returns_empty(tmp_path):
    state = load_state(tmp_path / "state.json")
    assert state.seen_ids == set()
    assert state.consecutive_failures == 0
    assert state.initialized is False


def test_save_then_load_roundtrip(tmp_path):
    path = tmp_path / "state.json"
    save_state(path, State(seen_ids={"111", "222"}, consecutive_failures=2, initialized=True))
    state = load_state(path)
    assert state.seen_ids == {"111", "222"}
    assert state.consecutive_failures == 2
    assert state.initialized is True
