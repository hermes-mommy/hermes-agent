from pathlib import Path
import re
import sys

ROOT = Path(r"C:\Users\faizz\guinevere")
ADR_DIR = ROOT / "adr"
expected_docs = [
    "Guinevere_BRD_v2.0.md",
    "Guinevere_PRD_v2.0.md",
    "Guinevere_TechnicalArchitecture_v2.0.md",
    "Guinevere_MemorySchema_v2.0.md",
    "Guinevere_AgentLoopSpec_v2.0.md",
    "Guinevere_APIIntegration_v2.0.md",
    "Guinevere_Persona_Document_v2.0.md",
]
required_sections = [
    "## Status", "## Date", "## Deciders", "## Tags", "## Risk Level",
    "## Supersedes", "## Related Documents", "## Context", "## Decision Drivers",
    "## Considered Options", "## Decision Outcome", "## Consequences", "### Positive",
    "### Negative", "### Risks", "## Links"
]
required_canonical = [
    "GPT-5.5 via 9Router",
    "DeepSeek V4 Flash via 9Router",
    "OpenRouter is not a fallback path",
    "PostgreSQL primary storage plus Redis cache",
    "exactly 7 phases",
    "fully replaces OpenCode/opencode",
    "Prometheus + Grafana run on the primary VPS first",
    "Wearable integrations are post-MVP",
    "obscura as primary and Playwright as fallback",
]
errors = []
adr_files = sorted(ADR_DIR.glob("ADR-*.md"))
if len(adr_files) != 25:
    errors.append(f"Expected 25 ADR files, found {len(adr_files)}")
nums = []
for path in adr_files:
    text = path.read_text(encoding="utf-8")
    m = re.match(r"ADR-(\d{3})-", path.name)
    if not m:
        errors.append(f"Bad filename: {path.name}")
        continue
    num = int(m.group(1))
    nums.append(num)
    if not text.startswith("---\n"):
        errors.append(f"{path.name}: missing YAML frontmatter start")
    if f"# ADR-{num:03d}:" not in text:
        errors.append(f"{path.name}: missing ADR heading")
    for section in required_sections:
        if section not in text:
            errors.append(f"{path.name}: missing section {section}")
    for marker in ["adr:", "title:", "status:", "date:", "deciders:", "tags:", "risk_level:", "supersedes:", "related_documents:"]:
        if marker not in text.split("---", 2)[1]:
            errors.append(f"{path.name}: frontmatter missing {marker}")
    if "[`../Guinevere_ADR_Index_v1.0.md`](../Guinevere_ADR_Index_v1.0.md)" not in text:
        errors.append(f"{path.name}: missing index link")
    if not any(doc in text for doc in expected_docs) and "AGENTS.md" not in text:
        errors.append(f"{path.name}: no source doc reference")
    for marker in required_canonical:
        if marker not in text:
            errors.append(f"{path.name}: missing canonical marker {marker}")
if nums != list(range(1, 26)):
    errors.append(f"ADR numbers not contiguous 001-025: {nums}")
index = ROOT / "Guinevere_ADR_Index_v1.0.md"
readme = ADR_DIR / "README.md"
for path in [index, readme]:
    if not path.exists():
        errors.append(f"Missing {path}")
    else:
        text = path.read_text(encoding="utf-8")
        for marker in ["Global Safe Word Principle", "Canonical Decision Map", "Backlog for Future ADRs", "adr_count: 25"]:
            if marker not in text:
                errors.append(f"{path.name}: missing {marker}")
        for n in range(1, 26):
            if f"ADR-{n:03d}" not in text:
                errors.append(f"{path.name}: missing ADR-{n:03d}")
for doc in expected_docs:
    if not (ROOT / doc).exists():
        errors.append(f"Missing source doc {doc}")
report = ROOT / "evidence" / "adr-generation" / "verification-report.md"
if errors:
    report.write_text("# ADR Batch Verification\n\nFAIL\n\n" + "\n".join(f"- {e}" for e in errors) + "\n", encoding="utf-8")
    print("FAIL")
    for e in errors:
        print(e)
    sys.exit(1)
report.write_text("# ADR Batch Verification\n\nPASS\n\n- 25 ADR files found and numbered ADR-001 through ADR-025.\n- Root index and adr/README.md found.\n- YAML frontmatter markers present.\n- MADR section markers present.\n- Canonical decision markers present in every ADR.\n- Every ADR links back to Guinevere_ADR_Index_v1.0.md and at least one source authority document.\n", encoding="utf-8")
print("PASS")
