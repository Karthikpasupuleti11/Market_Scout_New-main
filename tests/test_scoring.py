from nodes.scoring import (
    _verification_score,
    _authority_score,
)


def test_verification_score_single_source():
    score = _verification_score(1)

    assert score == 0.4


def test_verification_score_multiple_sources():
    score = _verification_score(3)

    assert score > 0.4


def test_authority_score_valid():
    score = _authority_score(0.8)

    assert score == 0.8


def test_authority_score_clamps_high():
    score = _authority_score(5)

    assert score == 1.0


def test_authority_score_clamps_low():
    score = _authority_score(-2)

    assert score == 0.0