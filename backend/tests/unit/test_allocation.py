from app.domain.allocation import FirstAvailableStrategy, StorageCandidate, SuitableSizeStrategy
from app.domain.enums import PackageSize as Z


def loc(i, code, size, cap=5, occ=0, active=True):
    return StorageCandidate(id=i, code=code, capacity=cap, occupied=occ, max_package_size=size, is_active=active)


CANDIDATES = [
    loc(1, "B-L1", Z.LARGE),
    loc(2, "A-M1", Z.MEDIUM, occ=4),
    loc(3, "C-S1", Z.SMALL, occ=1),
    loc(4, "A-S0", Z.SMALL, occ=5),  # full
    loc(5, "A-S9", Z.SMALL, active=False),
]


def test_first_available_uses_code_order_and_skips_full_and_inactive():
    ranked = FirstAvailableStrategy().rank(CANDIDATES, Z.SMALL)
    assert [c.code for c in ranked] == ["A-M1", "B-L1", "C-S1"]


def test_suitable_size_prefers_the_tightest_fitting_class():
    ranked = SuitableSizeStrategy().rank(CANDIDATES, Z.SMALL)
    assert [c.code for c in ranked] == ["C-S1", "A-M1", "B-L1"]


def test_large_package_only_fits_large_locations():
    for strategy in (FirstAvailableStrategy(), SuitableSizeStrategy()):
        assert [c.code for c in strategy.rank(CANDIDATES, Z.LARGE)] == ["B-L1"]


def test_ties_go_to_the_location_with_more_free_slots():
    ranked = SuitableSizeStrategy().rank([loc(1, "M-A", Z.MEDIUM, occ=3), loc(2, "M-B", Z.MEDIUM, occ=1)], Z.MEDIUM)
    assert ranked[0].code == "M-B"


def test_no_candidate_returns_empty_list():
    assert SuitableSizeStrategy().rank([loc(1, "S", Z.SMALL, cap=1, occ=1)], Z.SMALL) == []
