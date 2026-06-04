"""Assemble P11 step files into StepPrompts.md — same pattern as P9/P10 assembly."""
import os
import re

steps_dir = os.path.join('research-reports', 'p11-expansion')
step_prompts = os.path.join('stepprompts', 'StepPrompts.md')

# Read all 23 P11 step files in order
content_parts = []
for i in range(1, 24):
    fname = f'P11-{i:03d}.md'
    fpath = os.path.join(steps_dir, fname)
    with open(fpath, 'r', encoding='utf-8') as f:
        step_content = f.read().strip()
    content_parts.append(step_content)
    print(f'  Read {fname}: {len(step_content)} chars')

print(f'\nTotal step files: {len(content_parts)}')

# Build P11 section
p11_section = """## Phase 11: WhatsApp Integration (Expansion)

**Goal:** WhatsApp messaging integration via Neonize (pure Python whatsmeow wrapper)
**Steps:** 23
**Dependencies:** P5 (Agent Loop) + P8 (Observability/MVP Gate)
**Cost:** $0/month (Neonize is free, no Meta Cloud API)
**Evidence Path:** `evidence/phase-11/`
**Library:** Neonize v0.3.18 (pure Python, wraps Go whatsmeow) — see ADR-022 revision
**Hosting:** Same VPS, separate `guinevere-whatsapp.service` systemd unit
**ADR-022 Note:** Requires revision from Baileys/Node.js to Neonize/pure Python

### Steps

""" + '\n\n'.join(content_parts) + '\n'

# Read StepPrompts.md
with open(step_prompts, 'r', encoding='utf-8') as f:
    lines = f.readlines()

print(f'StepPrompts.md: {len(lines)} lines')

# Find P11 section boundaries
p11_start = None
p11_end = None
for idx, line in enumerate(lines):
    if '## Phase 11: WhatsApp Integration' in line:
        p11_start = idx
    elif p11_start is not None and line.startswith('## Phase 12:'):
        p11_end = idx
        break

if p11_start is None or p11_end is None:
    print(f'ERROR: P11 boundaries not found. start={p11_start}, end={p11_end}')
    exit(1)

print(f'P11 section: lines {p11_start+1}-{p11_end} (replacing {p11_end - p11_start} lines)')

# Replace
new_lines = lines[:p11_start] + [p11_section + '\n---\n\n'] + lines[p11_end:]

with open(step_prompts, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

# Verify
with open(step_prompts, 'r', encoding='utf-8') as f:
    content = f.read()

p11_headers = len(re.findall(r'### Step P11-\d{3}:', content))
total_lines = content.count('\n') + 1
print(f'\nVerification:')
print(f'  P11 step headers: {p11_headers} (expected 23)')
print(f'  Total lines: {total_lines}')
print(f'  PASS' if p11_headers == 23 else f'  FAIL')
