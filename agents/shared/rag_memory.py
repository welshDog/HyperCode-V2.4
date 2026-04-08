import hashlib
import os
from chromadb import PersistentClient
from typing import List

class AgentMemory:
    def __init__(self, agent_name: str, base_path: str = "./memory"):
        self.client = PersistentClient(path=os.path.join(base_path, agent_name))
        self.collection = self.client.get_or_create_collection(
            name=f"{agent_name}_knowledge",
            metadata={"description": "Agent's contextual memory"}
        )
    
    def ingest_document(self, doc_path: str, chunk_size: int = 1000):
        """Break Bible/Docs into chunks and store with embeddings"""
        if not os.path.exists(doc_path):
            return
            
        with open(doc_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Split into semantic chunks (by headers, paragraphs, etc.)
        chunks = self._smart_chunk(content, chunk_size)
        
        # Store each chunk with metadata
        for idx, chunk in enumerate(chunks):
            # Use SHA-256 for secure ID generation (replaced MD5)
            chunk_id = hashlib.sha256(chunk.encode()).hexdigest()
            # Check if exists first to avoid re-embedding
            existing = self.collection.get(ids=[chunk_id])
            if not existing['ids']:
                self.collection.add(
                    documents=[chunk],
                    ids=[chunk_id],
                    metadatas=[{"source": doc_path, "chunk_index": idx}]
                )
    
    def query_relevant_context(self, task_description: str, top_k: int = 3) -> str:
        """Retrieve only relevant Bible sections for this task"""
        if self.collection.count() == 0:
            return ""
            
        results = self.collection.query(
            query_texts=[task_description],
            n_results=top_k
        )
        
        if not results['documents']:
            return ""
            
        return "\n\n---\n\n".join(results['documents'][0])
    
    def _smart_chunk(self, text: str, size: int) -> List[str]:
        """Split by markdown headers first, then by size"""
        # Split by ## headers
        sections = text.split('\n## ')
        chunks = []
        
        for section in sections:
            # Re-add the header marker if it wasn't the first empty split
            if not section.startswith("## ") and section.strip():
                section = "## " + section
                
            if len(section) <= size:
                chunks.append(section)
            else:
                # Further split large sections
                lines = section.split('\n')
                current_chunk = []
                current_size = 0
                
                for line in lines:
                    current_size += len(line) + 1
                    if current_size > size:
                        chunks.append('\n'.join(current_chunk))
                        current_chunk = [line]
                        current_size = len(line)
                    else:
                        current_chunk.append(line)
                
                if current_chunk:
                    chunks.append('\n'.join(current_chunk))
        
        return chunks
