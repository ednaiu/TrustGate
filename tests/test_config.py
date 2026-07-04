from pathlib import Path

from trustgate.config import Config

REPO_WEIGHTS = Path(__file__).parent.parent / "weights.toml"


def test_repo_weights_toml_matches_builtin_defaults():
    # weights.toml documents the defaults; if they drift apart, one of them lies
    from_file = Config(REPO_WEIGHTS)
    builtin = Config()
    assert from_file.penalties == builtin.penalties
    assert from_file.thresholds == builtin.thresholds
    assert from_file.dynamic == builtin.dynamic
    assert from_file.mutation == builtin.mutation
    assert from_file.saturation == builtin.saturation


def test_custom_config_overrides(tmp_path):
    cfg_file = tmp_path / "custom.toml"
    cfg_file.write_text("[thresholds]\npass = 90\n\n[penalties]\nTG-D10 = 1\n")
    cfg = Config(cfg_file)
    assert cfg.thresholds["pass"] == 90
    assert cfg.penalties["TG-D10"] == 1
    assert cfg.penalties["TG-D01"] == 25  # untouched defaults stay


def test_downgraded_severity_uses_severity_table():
    cfg = Config()
    assert cfg.penalty_for("TG-D03", "critical") == 25  # its default severity
    assert cfg.penalty_for("TG-D03", "minor") == 5      # eval on a literal
