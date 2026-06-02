"""P3-004 verification script: download/cache all-MiniLM-L6-v2 and verify."""

import os
from pathlib import Path

from sentence_transformers import SentenceTransformer

MODEL_NAME = "all-MiniLM-L6-v2"
EXPECTED_DIMENSION = 384

print(f"Loading sentence-transformers model: {MODEL_NAME} ...")
model = SentenceTransformer(MODEL_NAME)

# Verify dimension with the non-deprecated API.
dimension = model.get_embedding_dimension()
print(f"Model dimension: {dimension}")
if dimension != EXPECTED_DIMENSION:
    raise RuntimeError(f"Expected {EXPECTED_DIMENSION}, got {dimension}")

# Cache path info. Dimension verification is sufficient for this cache-only step;
# embedding API/runtime behavior is covered by P3-005 after consent.

hf_home = Path(os.environ.get("HF_HOME", Path.home() / ".cache" / "huggingface"))
model_dir = hf_home / "hub" / "models--sentence-transformers--all-MiniLM-L6-v2"
print(f"\nHF_HOME: {hf_home}")
print(f"Model cache base: {model_dir}")
print(f"Model cache exists: {model_dir.exists()}")

if model_dir.exists():
    for root, _dirs, files in os.walk(model_dir):
        root_path = Path(root)
        level = len(root_path.relative_to(model_dir).parts) if root_path != model_dir else 0
        indent = " " * 2 * level
        print(f"{indent}{root_path.name}/")
        subindent = " " * 2 * (level + 1)
        for file_name in files:
            file_path = root_path / file_name
            print(f"{subindent}{file_name} ({file_path.stat().st_size} bytes)")

legacy_path = Path.home() / ".cache" / "torch" / "sentence_transformers"
print(f"\nLegacy torch ST path: {legacy_path}")
print(f"Legacy path exists: {legacy_path.exists()}")

print()
print("=== VERIFICATION PASSED ===")
print(f"all-MiniLM-L6-v2 confirmed: {dimension} dimensions")
print("Model cached at HuggingFace hub path (HF_HOME)")
print("Cache-ONLY evidence: 384-dim vectors must NOT be written to vector(1536) columns")