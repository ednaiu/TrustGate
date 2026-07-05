from trustgate.config import Config
from trustgate.findings import Finding
from trustgate.scoring import aggregate, dynamic_penalty, mutation_penalty

CFG = Config()


def make(detector, severity, n=1):
    return [Finding(detector, severity, i + 1, "x") for i in range(n)]


def test_clean_code_full_pass():
    raw, score, verdict = aggregate([], {"ran": True, "tests_total": 5, "tests_failed": 0},
                                    {"ran": True, "mutants_total": 10, "mutants_killed": 9,
                                     "mutation_score": 0.9}, CFG)
    assert (raw, score, verdict) == (100, 100, "PASS")


def test_partial_analysis_cannot_pass():
    raw, score, verdict = aggregate([], {"ran": True, "tests_total": 5, "tests_failed": 0},
                                    {"ran": False}, CFG, partial=True)
    assert (raw, score, verdict) == (90, 90, "REVIEW")


def test_single_critical_blocks():
    # calibrated on corpus v1: one critical finding blocks with precision 1.0
    findings = make("TG-D01", "critical", 1)
    _, score, verdict = aggregate(findings, None, {"ran": False}, CFG)
    assert verdict == "BLOCK"


def test_criticals_do_not_saturate():
    # 5 hallucinated imports: 5*25 = 125 > saturation cap, must reach BLOCK
    findings = make("TG-D01", "critical", 5)
    raw, score, verdict = aggregate(findings, None, None, CFG)
    assert raw < 0
    assert score == 0
    assert verdict == "BLOCK"


def test_major_saturation_caps_at_40():
    # 10 dead-code findings at 5 pts each would be 50, cap is 40
    findings = make("TG-D10", "minor", 10)
    raw, _, _ = aggregate(findings, None, {"ran": True, "mutation_score": 0.9,
                                           "mutants_total": 1, "mutants_killed": 1}, CFG)
    assert raw == 100 - 40


def test_raw_score_invariant():
    findings = make("TG-D08", "major", 2)
    dynamic = {"ran": True, "tests_total": 4, "tests_failed": 2, "timeout": False}
    mutation = {"ran": False}
    raw, score, _ = aggregate(findings, dynamic, mutation, CFG)
    spent = sum(f.penalty for f in findings) \
        + dynamic_penalty(dynamic, CFG) + mutation_penalty(mutation, CFG)
    assert raw == 100 - spent
    assert score == max(0, raw)


def test_missing_mutation_penalty_is_uniform():
    # all four "no mutation verdict" paths cost the same (NS-13)
    paths = [None, {"ran": False}, {"ran": False, "reason": "no_tests"},
             {"ran": False, "reason": "disabled"}]
    penalties = {mutation_penalty(p, CFG) for p in paths}
    assert penalties == {CFG.mutation["missing"]}


def test_mutation_thresholds_boundaries():
    def pen(score):
        return mutation_penalty({"ran": True, "mutation_score": score,
                                 "mutants_total": 10, "mutants_killed": 0}, CFG)
    assert pen(0.0) == 20
    assert pen(0.39) == 20
    assert pen(0.4) == 10
    assert pen(0.69) == 10
    assert pen(0.7) == 0
    assert pen(1.0) == 0


def test_dynamic_fail_cap():
    d = {"ran": True, "tests_total": 20, "tests_failed": 10, "timeout": False}
    assert dynamic_penalty(d, CFG) == CFG.dynamic["fail_cap"]


def test_verdict_boundaries():
    # PASS >= 76, REVIEW 40..75, BLOCK <= 39; any critical -> BLOCK (corpus v1)
    clean_dynamic = {"ran": True, "tests_total": 1, "tests_failed": 0}
    clean_mutation = {"ran": True, "mutation_score": 1.0,
                      "mutants_total": 1, "mutants_killed": 1}

    def verdict_for(findings, expected_score):
        _, score, verdict = aggregate(findings, clean_dynamic, clean_mutation, CFG)
        assert score == expected_score
        return verdict

    # a critical finding blocks regardless of the remaining score
    assert verdict_for(make("TG-D04", "critical"), 80) == "BLOCK"
    assert verdict_for(make("TG-D01", "critical"), 75) == "BLOCK"
    # majors alone follow the score rule: -12 -> 88 PASS, saturated majors -> REVIEW
    assert verdict_for(make("TG-D06", "major"), 88) == "PASS"
    assert verdict_for(make("TG-D06", "major", 4), 60) == "REVIEW"
