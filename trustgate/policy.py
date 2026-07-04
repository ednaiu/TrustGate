"""Policy model for CI decisions and roles."""
import sys
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


DEFAULT_POLICY = {
    "fail_on_review": False,
    "require_project_tests": False,
    "require_project_mutation": False,
    "max_findings": None,
    "max_critical_findings": 0,
}

DEFAULT_ROLES = {
    "viewer": {"permissions": ["read"]},
    "reviewer": {"permissions": ["read", "comment", "approve_review"]},
    "maintainer": {"permissions": ["read", "comment", "override_block", "manage_policy"]},
}


def load_policy(path: Path | str | None) -> dict:
    if path is None:
        return {"policy": dict(DEFAULT_POLICY), "roles": dict(DEFAULT_ROLES), "users": {}}
    with open(path, "rb") as f:
        data = tomllib.load(f)
    return {
        "policy": {**DEFAULT_POLICY, **data.get("policy", {})},
        "roles": {**DEFAULT_ROLES, **data.get("roles", {})},
        "users": data.get("users", {}),
    }


def validate_role(policy_data: dict, role: str | None) -> None:
    if not role:
        return
    if role not in policy_data.get("roles", {}):
        known = ", ".join(sorted(policy_data.get("roles", {})))
        raise ValueError(f"unknown policy role '{role}', known roles: {known}")


def resolve_role(policy_data: dict, user: str | None, role: str | None) -> str | None:
    if role:
        validate_role(policy_data, role)
        return role
    if not user:
        return None
    users = policy_data.get("users", {})
    if user not in users:
        known = ", ".join(sorted(users)) or "no users configured"
        raise ValueError(f"unknown policy user '{user}', known users: {known}")
    item = users[user]
    resolved = item.get("role") if isinstance(item, dict) else str(item)
    validate_role(policy_data, resolved)
    return resolved


def apply_policy(scan_report: dict, policy_data: dict) -> dict:
    out = dict(scan_report)
    rules = policy_data.get("policy", DEFAULT_POLICY)
    triggered = []

    if rules.get("require_project_tests") and not out.get("dynamic", {}).get("ran"):
        triggered.append("require_project_tests")
    if rules.get("require_project_mutation") and not out.get("mutation", {}).get("ran"):
        triggered.append("require_project_mutation")
    max_findings = rules.get("max_findings")
    if max_findings is not None and out["summary"]["findings"] > int(max_findings):
        triggered.append("max_findings")
    max_critical = int(rules.get("max_critical_findings", 0))
    critical = sum(1 for item in out.get("findings", []) if item.get("severity") == "critical")
    if critical > max_critical:
        triggered.append("max_critical_findings")
    if rules.get("fail_on_review") and out["verdict"] == "REVIEW":
        triggered.append("fail_on_review")

    if triggered:
        out["verdict"] = "BLOCK"
        out["score"] = min(out["score"], 39)
    out["policy"] = {
        "applied": True,
        "triggered": triggered,
        "roles": sorted(policy_data.get("roles", {})),
        "active_role": policy_data.get("active_role"),
        "active_user": policy_data.get("active_user"),
    }
    return out
