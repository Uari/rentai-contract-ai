
import yaml, pathlib
RULES_DIR = pathlib.Path("rules")
DEFAULT_RULE = RULES_DIR / "rules_v1.yml"

def load_rules(path: pathlib.Path = DEFAULT_RULE):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def current_rule_version() -> str:
    rules = load_rules()
    return rules.get("version", "v1")
