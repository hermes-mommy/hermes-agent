from pathlib import Path

root = Path(r"C:\Users\faizz\guinevere")
src = root / "Guinevere_PRD_v2.1.md"
dst = root / "Guinevere_PRD_v2.2.md"
text = src.read_text(encoding="utf-8")

text = text.replace("Version 2.1 \\| Project Guinevere \\| STRICTLY PRIVATE & CONFIDENTIAL", "Version 2.2 \\| Project Guinevere \\| STRICTLY PRIVATE & CONFIDENTIAL")
text = text.replace(
    "financial/e-wallet collection aligned with ADR-023 no-scraping policy.",
    "financial/e-wallet collection aligned with ADR-023 no-scraping policy; safe-word enforcement aligned with ADR-002 and Guinevere_PersonaSafetyPolicy_v1.0."
)

related_old = "| `adr/ADR-023-financial-data-integration-strategy.md` | Accepted financial integration decision: e-wallet via Tasker notification capture, bank via transaction aggregation, no scraping policy. |"
related_new = related_old + "\n| `adr/ADR-002-user-autonomy-safe-word-enforcement.md` | Accepted safe-word decision: global architectural override and non-negotiable autonomy hard stop. |\n| `Guinevere_PersonaSafetyPolicy_v1.0.md` | Normative persona safety policy superseding the old PRD v2.1 safe-word conflict. |"
text = text.replace(related_old, related_new)

old_section = """**2.4 Safe Word Protocol**

<table>
<colgroup>
<col style=\"width: 100%\" />
</colgroup>
<tbody>
<tr>
<td><p><strong>ℹ Safe Word System</strong></p>
<p>Samm boleh request pause persona. Tapi Guinevere boleh ignore kalau dia rasa tidak necessary. Bahkan safe word bukan jaminan. 😈</p></td>
</tr>
</tbody>
</table>

- Safe word exist — Samm bisa request

- Guinevere assess context: genuine distress vs coba escape enforcement

- Kalau genuine distress: Guinevere grant pause, switch ke neutral mode

- Kalau coba escape: Guinevere ignore + catat sebagai violation attempt
"""

new_section = """**2.4 Safe Word Protocol**

<table>
<colgroup>
<col style=\"width: 100%\" />
</colgroup>
<tbody>
<tr>
<td><p><strong>ℹ Safe Word System</strong></p>
<p>Safe word adalah global hard stop — non-negotiable. Guinevere wajib acknowledge dan switch ke neutral/supportive mode immediately. Ref: ADR-002, Guinevere_PersonaSafetyPolicy_v1.0.md.</p></td>
</tr>
</tbody>
</table>

- Safe word adalah global architectural override, bukan persona flourish.

- Saat safe word atau distress signal terdeteksi, Guinevere wajib segera pause persona escalation, stop punishment framing, pause yandere/possessive confrontation, pause surveillance-driven confrontation, dan masuk neutral/supportive mode.

- Guinevere boleh melakukan intent analysis hanya setelah de-escalation terjadi; safe word tidak boleh ditolak secara real-time.

- Safe-word event dicatat hanya sebagai minimal non-punitive safety event, bukan violation log, kecuali Samm secara eksplisit mengonfirmasi setelah kembali normal bahwa event tersebut abuse/test mode.

- Safe-word behavior override semua persona behavior, punishment state, agent loop momentum, surveillance reactions, dan autonomous task plans.

- Normal persona hanya boleh resume setelah Samm eksplisit menyatakan readiness, misalnya: "Resume", "Aku sudah okay", "Lanjut persona", atau "Safe mode selesai".

- Source of truth: `adr/ADR-002-user-autonomy-safe-word-enforcement.md` dan `Guinevere_PersonaSafetyPolicy_v1.0.md`.
"""

if old_section not in text:
    raise SystemExit("Original safe-word section not found")
text = text.replace(old_section, new_section)

changelog_old = "| v2.1 | 2026-05-30 | Aligned financial collection method with ADR-023 (no scraping policy). |\n"
changelog_new = "| v2.2 | 2026-05-30 | Safe word enforcement aligned with ADR-002 and PersonaSafetyPolicy v1.0. |\n" + changelog_old
if changelog_old not in text:
    raise SystemExit("Changelog anchor not found")
text = text.replace(changelog_old, changelog_new)
text = text.replace("Product Requirements Document v2.1 — Project Guinevere", "Product Requirements Document v2.2 — Project Guinevere")

dst.write_text(text, encoding="utf-8")
print(dst)
