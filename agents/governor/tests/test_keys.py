import pytest

import keys


def test_missing_key_raises(monkeypatch):
    """Test missing key raises."""
    monkeypatch.delenv("GOVERNOR_PRIVATE_KEY_PEM", raising=False)
    monkeypatch.setenv("GOVERNOR_PRIVATE_KEY_FILE", "/nonexistent/path")
    with pytest.raises(RuntimeError, match="signing key not configured"):
        keys.load_private_key()


def test_env_pem_round_trips(monkeypatch, tmp_path):
    """Test env pem round trips."""
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
    monkeypatch.setenv("GOVERNOR_PRIVATE_KEY_PEM", priv_pem)
    pub_file = tmp_path / "pub.pem"
    pub_file.write_text(pub_pem)
    monkeypatch.setenv("GOVERNOR_PUBLIC_KEY_FILE", str(pub_file))

    import pyseto

    token = pyseto.encode(keys.load_private_key(), payload={"k": "v"}, serializer=__import__("json"))
    decoded = pyseto.decode(keys.load_public_key(), token, deserializer=__import__("json"))
    assert decoded.payload == {"k": "v"}
