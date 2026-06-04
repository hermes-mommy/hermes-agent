"""Assemble P9+P10 Tier 1 step prompts into StepPrompts.md"""
import os, sys

base = r'C:\Users\faizz\guinevere'
sp_path = os.path.join(base, 'stepprompts', 'StepPrompts.md')
src_dir = os.path.join(base, 'research-reports', 'p9-p10-expansion')

with open(sp_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Build P9 replacement section
p9_header = """## Phase 9: Financial Tracking (Stabilization)

**Phase Goal:** Financial data model, Tasker SMS capture, classification, budget tracking, Discord commands, PDF reports, Grafana dashboard, provider cost attribution, E2E test
**Step Count:** 13 | **Cost:** $1/month | **Dependencies:** P8 complete (MVP delivered)
**Estimated Duration:** 4-5 days
**ADR References:** ADR-023, ADR-009, ADR-004, ADR-006, ADR-017, ADR-024, ADR-027, ADR-032
**Acceptance Criteria:** AC-FIN-001..006, AC-PHASE-009

"""
p9_parts = [p9_header]
for i in range(1, 14):
    fpath = os.path.join(src_dir, f'P9-{i:03d}.md')
    with open(fpath, 'r', encoding='utf-8') as f:
        p9_parts.append(f.read().strip())
        p9_parts.append('\n\n---\n\n')
p9_section = ''.join(p9_parts).rstrip()

# Build P10 replacement section
p10_header = """## Phase 10: Production Hardening (Stabilization)

**Phase Goal:** Security audit, performance tuning, systemd hardening, backup/DR, CI/CD, key rotation, rate limiting, CORS, health checks, graceful shutdown, load testing, hardening verification, MVP acceptance gate
**Step Count:** 21 | **Cost:** $1/month | **Dependencies:** P8 complete
**Estimated Duration:** 7-10 days
**ADR References:** ADR-018, ADR-016, ADR-025, ADR-032, ADR-015, ADR-014, ADR-029, ADR-008, ADR-017, ADR-027, ADR-030, ADR-019
**Acceptance Criteria:** AC-SEC-001..007, AC-OPS-001..006, AC-CORE-001..006, AC-PHASE-006, AC-PHASE-007, AC-PHASE-010

"""
p10_parts = [p10_header]
for i in range(1, 22):
    fpath = os.path.join(src_dir, f'P10-{i:03d}.md')
    with open(fpath, 'r', encoding='utf-8') as f:
        p10_parts.append(f.read().strip())
        p10_parts.append('\n\n---\n\n')
p10_section = ''.join(p10_parts).rstrip()

# Find section boundaries
p9_marker = '## Phase 9: Financial Tracking (Stabilization)'
p10_marker = '## Phase 10: Production Hardening (Stabilization)'
p11_marker = '## Phase 11: WhatsApp Integration (Expansion)'

idx_p9 = content.find(p9_marker)
idx_p10 = content.find(p10_marker)
idx_p11 = content.find(p11_marker)

print(f'P9 start: {idx_p9}')
print(f'P10 start: {idx_p10}')
print(f'P11 start: {idx_p11}')

if idx_p9 < 0 or idx_p10 < 0 or idx_p11 < 0:
    print('ERROR: could not find section markers')
    sys.exit(1)

# Build new content: before P9 + new P9 + new P10 + P11 onwards
before_p9 = content[:idx_p9]
after_p10 = content[idx_p11:]

new_content = before_p9 + p9_section + '\n\n---\n\n' + p10_section + '\n\n---\n\n' + after_p10

with open(sp_path, 'w', encoding='utf-8') as f:
    f.write(new_content)

# Verify
old_lines = content.count('\n')
new_lines = new_content.count('\n')
p9_count = new_content.count('### Step P9-')
p10_count = new_content.count('### Step P10-')
print(f'Old lines: {old_lines}')
print(f'New lines: {new_lines}')
print(f'P9 step headers: {p9_count} (expect 13)')
print(f'P10 step headers: {p10_count} (expect 21)')

# Verify no old content remains
has_old_grouped = '### Steps P9-001 to P9-012' in new_content
has_old_p18b = '### Step P10-018b:' in new_content
print(f'Old P9 grouped format present: {has_old_grouped}')
print(f'Old P10-018b present: {has_old_p18b}')

if p9_count == 13 and p10_count == 21 and not has_old_grouped and not has_old_p18b:
    print('SUCCESS: StepPrompts.md updated correctly')
else:
    print('WARNING: verification failed, check output')
