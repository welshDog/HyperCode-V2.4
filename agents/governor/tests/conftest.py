import os
import sys

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# Add parent directory to path to import main
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(scope="session", autouse=True)
def _ephemeral_signing_key(tmp_path_factory):
    """Give every governor test a working Ed25519 keypair without needing
    secrets/ or a committed PEM. Only fills in what isn't already set, so a
    test that deliberately unsets the key (test_keys.py) still works."""
    import os

    if os.getenv("GOVERNOR_PRIVATE_KEY_PEM"):
        yield
        return

    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    priv = Ed25519PrivateKey.generate()
    priv_pem = priv.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
    pub_pem = (
        priv.public_key()
        .public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
        .decode()
    )
    pub_file = tmp_path_factory.mktemp("gov-keys") / "governor_public_key.pem"
    pub_file.write_text(pub_pem)
    os.environ["GOVERNOR_PRIVATE_KEY_PEM"] = priv_pem
    os.environ["GOVERNOR_PUBLIC_KEY_FILE"] = str(pub_file)
    yield


@pytest_asyncio.fixture
async def client():
    """Helper: client."""
    import main

    async with AsyncClient(transport=ASGITransport(app=main.app), base_url="http://test") as ac:
        yield ac
