from botocore.exceptions import ClientError


def test_storage_upload_returns_none_when_client_unavailable(monkeypatch):
    import app.core.storage as storage_mod

    class DummyService(storage_mod.StorageService):
        def __init__(self):
            self.endpoint = "x"
            self.access_key = "x"
            self.secret_key = "x"
            self.bucket_name = "b"
            self.secure = False
            self.s3_client = None

    svc = DummyService()
    assert svc.upload_file("data", "f.md") is None


def test_storage_ensure_bucket_creates_on_404(monkeypatch):
    import app.core.storage as storage_mod

    calls: dict = {"create_bucket": 0}

    class DummyClient:
        def head_bucket(self, Bucket: str):
            raise ClientError({"Error": {"Code": "404"}}, "HeadBucket")

        def create_bucket(self, Bucket: str):
            calls["create_bucket"] += 1

        def upload_fileobj(self, *a, **k):
            return None

    class DummyService(storage_mod.StorageService):
        def __init__(self):
            self.endpoint = "x"
            self.access_key = "x"
            self.secret_key = "x"
            self.bucket_name = "b"
            self.secure = False
            self.s3_client = DummyClient()

    svc = DummyService()
    key = svc.upload_file("hello", "x.md", metadata={"a": "b"})
    assert key == "b/x.md"
    assert calls["create_bucket"] == 1


def test_storage_get_storage_is_singleton(monkeypatch):
    import app.core.storage as storage_mod

    storage_mod._storage_service = None

    first = storage_mod.get_storage()
    second = storage_mod.get_storage()
    assert first is second

