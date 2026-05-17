from listam_notifier.parser import Listing
from listam_notifier.state import State
from listam_notifier.main import select_ongoing_new


def _l(i):
    return Listing(str(i), f"https://www.list.am/item/{i}", f"Apt {i}",
                   "280,000", "Yerevan", None)


def test_select_ongoing_new_returns_unseen_ids():
    listings = [_l(1), _l(2), _l(3)]
    state = State(seen_ids={"1", "2"}, initialized=True)
    assert [l.item_id for l in select_ongoing_new(listings, state)] == ["3"]


def test_select_ongoing_new_empty_when_all_seen():
    listings = [_l(1), _l(2)]
    state = State(seen_ids={"1", "2"}, initialized=True)
    assert select_ongoing_new(listings, state) == []
