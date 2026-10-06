from pathlib import Path
import base64, gzip, hashlib

root = Path(__file__).resolve().parent
encoded = (root / "main.go.gz.b64").read_text(encoding="ascii").strip()
data = gzip.decompress(base64.b64decode(encoded))
sha = hashlib.sha256(data).hexdigest()
expected = "825139bfc2a54648a1f406261d47d60815a26879b2cb6d67310653f45f8a9741"
if sha != expected:
    raise SystemExit(f"main.go SHA-256 mismatch: {sha}")
(root / "main.go").write_bytes(data)
print(f"restored main.go ({len(data)} bytes), SHA-256 {sha}")
