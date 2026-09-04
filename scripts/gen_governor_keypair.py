"""Generate the governor Ed25519 keypair.

Private PEM -> secrets/governor_ed25519_private_key.txt  (gitignored)
Public  PEM -> agents/governor/governor_public_key.pem
               agents/fleet-controller/governor_public_key.pem   (file-copy: verifiers vendor the public key)

Run once per environment. Re-running rotates the key (invalidates every
live capability — do it during a maintenance window).
"""
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

(ROOT / "secrets").mkdir(exist_ok=True)
(ROOT / "secrets" / "governor_ed25519_private_key.txt").write_bytes(priv_pem)
for rel in ("agents/governor/governor_public_key.pem", "agents/fleet-controller/governor_public_key.pem"):
    (ROOT / rel).write_bytes(pub_pem)
print("wrote private key to secrets/ and public key to both agent dirs")
