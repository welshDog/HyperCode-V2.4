import logging
import chromadb
from chromadb.utils import embedding_functions
from app.core.config import settings
from typing import List, Dict, Any
import uuid
from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)

class RAGService:
    """
    Manages Vector Memory (RAG) using ChromaDB.
    Handles embedding generation, chunking, storage, and retrieval.
    """
    def __init__(self):
        self.host = settings.CHROMA_HOST
        self.port = settings.CHROMA_PORT
        self.collection_name = "hypercode_memory"
        self.client = None
        self.collection = None
        self.embedding_fn = None
        
        # Text Splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )

        # Lazy connection (don't connect on import)
        # self._connect()

    def _get_embedding_function(self):
        if self.embedding_fn:
            return self.embedding_fn
            
        try:
            logger.info(f"[RAG] Loading embedding model: {settings.EMBEDDING_MODEL}")
            self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=settings.EMBEDDING_MODEL
            )
        except Exception as e:
            logger.warning(f"[RAG] Failed to load local embedding model: {e}. Falling back to default.")
            self.embedding_fn = embedding_functions.DefaultEmbeddingFunction()
        return self.embedding_fn

    def _connect(self):
        """
        Establishes connection to ChromaDB.
        """
        try:
            logger.info(f"[RAG] Connecting to ChromaDB at {self.host}:{self.port}...")
            self.client = chromadb.HttpClient(host=self.host, port=self.port)
            
            # Create or get collection
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                embedding_function=self._get_embedding_function(),
                metadata={"hnsw:space": "cosine"} # Optimization for similarity search
            )
            logger.info(f"[RAG] Connected to collection: {self.collection_name}")
        except Exception as e:
            logger.error(f"[RAG] Connection failed: {e}")
            self.client = None

    def ingest_document(self, content: str, source: str, metadata: Dict[str, Any] = None) -> int:
        """
        Chunks and stores a document in the vector database.
        Returns the number of chunks stored.
        """
        if not self.client:
            self._connect()
            if not self.client:
                return 0

        try:
            # 1. Chunking
            chunks = self.text_splitter.split_text(content)
            if not chunks:
                return 0

            # 2. Prepare Data
            ids = [f"{source}_{uuid.uuid4().hex[:8]}_{i}" for i in range(len(chunks))]
            metadatas = []
            for i in range(len(chunks)):
                meta = metadata.copy() if metadata else {}
                meta.update({
                    "source": source,
                    "chunk_index": i,
                    "total_chunks": len(chunks)
                })
                metadatas.append(meta)

            # 3. Add to Chroma
            self.collection.add(
                documents=chunks,
                metadatas=metadatas,
                ids=ids
            )
            
            logger.info(f"[RAG] Ingested {len(chunks)} chunks from {source}")
            return len(chunks)

        except Exception as e:
            logger.error(f"[RAG] Ingestion failed for {source}: {e}")
            return 0

    def query(self, query_text: str, n_results: int = 5, filters: Dict = None) -> List[str]:
        """
        Semantic search for relevant context.
        """
        if not self.client:
            self._connect()
            if not self.client:
                return []

        try:
            results = self.collection.query(
                query_texts=[query_text],
                n_results=n_results,
                where=filters # Optional metadata filtering
            )
            
            # Flatten results (Chroma returns list of lists)
            documents = results['documents'][0] if results['documents'] else []
            return documents

        except Exception as e:
            logger.error(f"[RAG] Query failed: {e}")
            return []

    def reset(self):
        """
        Clears all memory. Use with caution.
        """
        if self.client:
            self.client.reset()
            self._connect()

# Global Instance
rag = RAGService()
