from pathlib import Path

ROOT = Path(r"C:\Users\faizz\guinevere")
paths = list((ROOT / "adr").glob("*.md")) + [ROOT / "Guinevere_ADR_Index_v1.0.md"]
for path in paths:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    normalized = []
    for line in lines:
        if line.startswith("    "):
            normalized.append(line[4:])
        else:
            normalized.append(line)
    path.write_text("\n".join(normalized) + "\n", encoding="utf-8")
print(f"Normalized {len(paths)} markdown files")
