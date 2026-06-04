"""Assemble P12 section in StepPrompts.md from 29 individual step files."""
import pathlib

ROOT = pathlib.Path(r"C:\Users\faizz\guinevere")
SRC = ROOT / "research-reports" / "p12-expansion"
TARGET = ROOT / "stepprompts" / "StepPrompts.md"

# Read all 29 step files
parts = []
for i in range(1, 30):
    fpath = SRC / f"P12-{i:03d}.md"
    if not fpath.exists():
        raise FileNotFoundError(f"Missing: {fpath}")
    parts.append(fpath.read_text(encoding="utf-8").rstrip())

assembled = "\n\n".join(parts) + "\n"

# Read StepPrompts.md
lines = TARGET.read_text(encoding="utf-8").splitlines(keepends=True)

# Find P12 section boundaries
p12_start = None
p13_start = None
for idx, line in enumerate(lines):
    if line.startswith("## Phase 12: Gmail"):
        p12_start = idx
    elif line.startswith("## Phase 13: X Auto"):
        p13_start = idx
        break

if p12_start is None or p13_start is None:
    raise RuntimeError(f"Could not find boundaries: p12={p12_start}, p13={p13_start}")

# Find the --- separator before P13
sep_idx = p13_start - 1
while sep_idx > p12_start and lines[sep_idx].strip() == "":
    sep_idx -= 1
# sep_idx should be the "---" line before P13

# Replace: from p12_start to sep_idx (exclusive of ---)
new_section = f"""## Phase 12: Gmail/Email Integration (Expansion)

**Goal:** Gmail/Email read, notify, classify, draft, and trigger agent loops
**Steps:** 29
**Dependencies:** P5 (Agent Loop) + P8 (Observability/MVP Gate)
**Cost:** $0/month (Gmail API free tier + Resend free tier)
**Evidence Path:** `evidence/phase-12/`

### Steps

{assembled}

### Phase Complete Criteria
- [ ] All 29 steps complete
- [ ] AC-EMAIL-001 through AC-EMAIL-009 met
- [ ] AC-PHASE-012 (P12 exit) satisfied
- [ ] Evidence documented in `evidence/phase-12/`

### Verification
- [ ] P12 GATE: 10 integration test scenarios pass
- [ ] Gmail API OAuth2 flow verified
- [ ] Push notification pipeline verified
- [ ] Email classification cascade verified
- [ ] Draft generation + Discord approval flow verified
- [ ] Cross-channel HARD STOP verified
- [ ] Financial email → P9 bridge verified
- [ ] Agent loop trigger verified
- [ ] Grafana dashboard provisioning verified
- [ ] Systemd service health verified

---

"""

new_lines = lines[:p12_start] + [new_section] + lines[sep_idx + 1:]
TARGET.write_text("".join(new_lines), encoding="utf-8")

# Verify
result = TARGET.read_text(encoding="utf-8")
count = result.count("### Step P12-")
total = len(result.splitlines())
print(f"P12 headers: {count}")
print(f"Total lines: {total}")
assert count == 29, f"Expected 29, got {count}"
print("PASS")
