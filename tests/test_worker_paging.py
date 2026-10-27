"""Paging through load stages and telling apart stages that look alike (export.Pager), against a
stand-in for a solved Response (no Wine needed)."""
import pytest

from r2x.worker.export import GENERAL, Look, Pager, thorough_look
from r2x.worker.session import VK_NEXT, VK_PRIOR, R2xError


class FakeScreen:
    """A solved Response as the pager sees it: per stage, a Longitudinal Strain and a Shear
    Strain export; PgUp and PgDn move one stage and stop at the ends."""

    def __init__(self, strain, shear, at):
        self.strain, self.shear, self.at = strain, shear, at
        self.view = "no-shear"
        self.switches = 0

    def copy_chart(self, chart):
        if chart.key == "longitudinal_strain":
            return self.strain[self.at]
        assert chart.key == "shear_strain" and self.view == "general", "Shear Strain is in General"
        return self.shear[self.at]

    def select_view(self, view):
        if view.name != self.view:
            self.view, self.switches = view.name, self.switches + 1

    def press(self, vk, times=1):
        step = {VK_PRIOR: 1, VK_NEXT: -1}[vk]
        for _ in range(times):
            self.at = min(max(self.at + step, 0), len(self.strain) - 1)


class Keys:
    """Stage keys whose value at each stage is the strain export's first byte."""

    def __init__(self, values):
        self.values = values

    @property
    def count(self):
        return len(self.values)

    def matches(self, strain, i):
        return strain[:1] == self.values[i]

    def candidates(self, strain):
        return [i for i in range(self.count) if self.matches(strain, i)]

    def check(self, strain, i):
        if not self.matches(strain, i):
            raise R2xError(f"stage {i}: does not match")


# V alone in the increment: εx stays 0 (the same strain profile) until the section cracks.
STRAIN = [b"0a", b"0b", b"0b", b"0b", b"1c", b"2d", b"3e", b"3e"]
SHEAR = [b"s0", b"s1", b"s2", b"s3", b"s4", b"s5", b"s6", b"s7"]
KEYS = Keys([s[:1] for s in STRAIN])


def test_a_thorough_look_pages_where_the_strain_profile_repeats():
    screen = FakeScreen(STRAIN, SHEAR, at=6)
    pager = Pager(screen, KEYS, thorough=True)
    here = pager.to_zero()
    assert screen.at == 0 and here == Look(b"0a", b"s0") and screen.view == GENERAL.name
    for i in range(1, 8):
        here = pager.up(here, i)
        assert screen.at == i and here == Look(STRAIN[i], SHEAR[i])
    pager.at_last(here)


def test_a_plain_look_is_the_strain_profile_alone():
    screen = FakeScreen(STRAIN, SHEAR, at=4)
    assert Pager(screen, KEYS, thorough=False).look() == Look(b"1c")
    assert screen.switches == 0                       # no view switch without shear


def test_find_tells_candidates_apart_by_their_exports():
    """The stage on screen is 2; its strain profile matches stages 1 to 3."""
    screen = FakeScreen(STRAIN, SHEAR, at=2)
    pager = Pager(screen, KEYS, thorough=True)
    opened = pager.look()
    candidates = KEYS.candidates(opened.strain)
    assert candidates == [0, 1, 2, 3]
    stage, here = pager.find(opened, candidates)
    assert stage == 2 and screen.at == 3 and here == Look(b"0b", b"s3")


def test_find_refuses_to_guess():
    strain = [b"0a", b"1b", b"2c", b"1b", b"3d"]
    shear = [b"s0", b"s", b"s2", b"s", b"s4"]              # 1 and 3 look exactly alike
    keys = Keys([x[:1] for x in strain])
    screen = FakeScreen(strain, shear, at=3)
    pager = Pager(screen, keys, thorough=True)
    opened = pager.look()
    with pytest.raises(R2xError, match="cannot tell which stage Response showed: its exports "
                                       "match stages 1,3"):
        pager.find(opened, keys.candidates(opened.strain))


def test_paging_past_the_last_stage_is_checked():
    screen = FakeScreen(STRAIN, SHEAR, at=7)
    pager = Pager(screen, KEYS, thorough=True)
    here = pager.look()
    screen.strain, screen.shear = STRAIN + [b"4f"], SHEAR + [b"s8"]   # one more stage
    with pytest.raises(R2xError, match="more than the 8 stages"):
        pager.at_last(here)


def test_when_a_look_needs_shear_strain():
    class K:
        repeats = []
    assert not thorough_look({"moment_ex": b"", "moment_phi": b""}, K)
    assert thorough_look({"shear_gxy": b"", "moment_phi": b""}, K)
    K.repeats = [1]                                        # an increment of 0,0,0
    assert thorough_look({"moment_ex": b"", "moment_phi": b""}, K)
