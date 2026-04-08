def test_rag_get_embedding_function_falls_back_on_exception(monkeypatch):
    import app.core.rag as rag_mod

    rag = rag_mod.RAGService()

    def raise_embed(*a, **k):
        raise RuntimeError("no model")

    monkeypatch.setattr(rag_mod.embedding_functions, "SentenceTransformerEmbeddingFunction", raise_embed)

    class DummyDefault:
        pass

    monkeypatch.setattr(rag_mod.embedding_functions, "DefaultEmbeddingFunction", lambda: DummyDefault())

    fn = rag._get_embedding_function()
    assert isinstance(fn, DummyDefault)


def test_rag_ingest_document_chunks_and_adds(monkeypatch):
    import app.core.rag as rag_mod

    rag = rag_mod.RAGService()
    rag.client = object()

    class DummyCollection:
        def __init__(self):
            self.add_calls: list[dict] = []

        def add(self, documents, metadatas, ids):
            self.add_calls.append({"documents": documents, "metadatas": metadatas, "ids": ids})

    rag.collection = DummyCollection()

    monkeypatch.setattr(rag.text_splitter, "split_text", lambda content: ["a", "b"])

    count = rag.ingest_document("content", "src", metadata={"k": "v"})
    assert count == 2
    assert rag.collection.add_calls[0]["documents"] == ["a", "b"]
    assert rag.collection.add_calls[0]["metadatas"][0]["source"] == "src"


def test_rag_query_returns_documents(monkeypatch):
    import app.core.rag as rag_mod

    rag = rag_mod.RAGService()
    rag.client = object()

    class DummyCollection:
        def query(self, query_texts, n_results, where=None):
            return {"documents": [["x", "y"]]}

    rag.collection = DummyCollection()

    docs = rag.query("q", n_results=2)
    assert docs == ["x", "y"]


def test_rag_reset_calls_client_and_reconnect(monkeypatch):
    import app.core.rag as rag_mod

    rag = rag_mod.RAGService()

    calls: dict = {"reset": 0, "connect": 0}

    class DummyClient:
        def reset(self):
            calls["reset"] += 1

    rag.client = DummyClient()

    def fake_connect():
        calls["connect"] += 1

    monkeypatch.setattr(rag, "_connect", fake_connect)

    rag.reset()
    assert calls["reset"] == 1
    assert calls["connect"] == 1
