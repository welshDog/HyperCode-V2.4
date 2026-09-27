"""BROski recover — restart eligibility policy (default-deny)."""

import pytest

from app.broski_operator.recover_policy import (
    ALLOW_LIST,
    NEVER_LIST,
    RESTARTABLE_LABEL,
    Eligibility,
    classify,
)

LABEL = {RESTARTABLE_LABEL: "restartable"}


@pytest.mark.parametrize("name", sorted(NEVER_LIST))
def test_never_list_always_blocked_even_with_label(name):
    assert classify(name).blocked_by == "never_list"
    elig = classify(name, LABEL)  # Review focus 3: label cannot override the never-list
    assert elig.allowed is False and elig.blocked_by == "never_list"


@pytest.mark.parametrize("name", sorted(ALLOW_LIST))
def test_allow_list_eligible(name):
    assert classify(name) == Eligibility(True, "allow_list", None)


def test_label_opt_in():
    assert classify("zz-recover-proof", LABEL) == Eligibility(True, "label", None)


def test_wrong_label_value_is_not_eligible():
    elig = classify("zz-x", {RESTARTABLE_LABEL: "true"})
    assert elig == Eligibility(False, None, "not_allowlisted")


def test_unknown_and_undecided_are_default_deny():
    for name in ("celery-worker", "hypercode-dashboard", "something-new"):
        assert classify(name) == Eligibility(False, None, "not_allowlisted")


def test_lists_are_disjoint():
    assert NEVER_LIST.isdisjoint(ALLOW_LIST)


def test_as_dict_shape():
    assert classify("skillweaver").as_dict() == {
        "allowed": True, "basis": "allow_list", "blocked_by": None,
    }
