"""Generate the governor Ed25519 keypair.

Private PEM -> secrets/governor_ed25519_private_key.txt  (gitignored)
Public  PEM -> agents/governor/governor_public_key.pem
               agents/fleet-controller/governor_public_key.pem   (file-copy: verifiers vendor the public key)

Run once per environment. Re-running rotates the key (invalidates every
live capability — do it during a maintenance window).
"""
import os
import stat
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parents[1]

priv = Ed25519PrivateKey.generate()
priv_pem = priv.private_bytes(
    serialization.Encoding.PEM,
    serialization.PrivateFormat.PKCS8,
    serialization.NoEncryption(),
)
pub_pem = priv.public_key().public_bytes(
    serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
)

secrets_dir = ROOT / "secrets"
secrets_dir.mkdir(exist_ok=True)
secrets_dir.chmod(stat.S_IRWXU)  # 0700 — owner-only

priv_key_path = secrets_dir / "governor_ed25519_private_key.txt"
fd = os.open(priv_key_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, stat.S_IRUSR | stat.S_IWUSR)  # 0600
with os.fdopen(fd, "wb") as f:
    f.write(priv_pem)

for rel in ("agents/governor/governor_public_key.pem", "agents/fleet-controller/governor_public_key.pem"):
    (ROOT / rel).write_bytes(pub_pem)
print("wrote private key to secrets/ and public key to both agent dirs")
