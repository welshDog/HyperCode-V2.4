"""Follow-up fix (parked residual R1/R2 from the governor Phase 2 final
review): _read_secret_file() must widen except OSError to also catch
UnicodeDecodeError, and read with utf-8-sig so a Windows-editor BOM is
stripped at read time instead of becoming part of the returned secret.
governor's ledger_client.py and main.py carry the identical function --
keep all three in sync.
"""
import safety_shepherd as ss


def test_reads_utf8_file_exactly(tmp_path):
    key_file = tmp_path / "key.txt"
    original = "s3cret-café-🔑"
    key_file.write_text(original, encoding="utf-8")
    assert ss._read_secret_file(str(key_file)) == original


def test_strips_utf8_bom(tmp_path):
    key_file = tmp_path / "key.txt"
    key_file.write_bytes(b"\xef\xbb\xbfsome-secret")
    assert ss._read_secret_file(str(key_file)) == "some-secret"


def test_missing_file_returns_empty(tmp_path):
    assert ss._read_secret_file(str(tmp_path / "does-not-exist.txt")) == ""


def test_non_utf8_file_fails_closed_instead_of_raising(tmp_path):
    """A secret file saved in a non-UTF-8 encoding (e.g. cp1252 with a
    byte sequence invalid as UTF-8) must return "" like a missing file,
    not raise UnicodeDecodeError into whatever called this."""
    key_file = tmp_path / "key.txt"
    key_file.write_bytes(b"\xff\xfe\x00bad")
    assert ss._read_secret_file(str(key_file)) == ""
