import asyncio
import os
import sys

# Add parent directory to path so we can import shared modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.shared.rag_memory import AgentMemory

async def test_rag():
    print("🧪 Testing RAG Memory System...")
    
    # Initialize memory
    memory = AgentMemory("test-agent", base_path="./agents/memory")
    
    # Create a dummy Bible file for testing if it doesn't exist
    bible_path = "./agents/HYPER-AGENT-BIBLE.md"
    if not os.path.exists(bible_path):
        print("⚠️ Bible not found, creating dummy content...")
        with open(bible_path, "w", encoding="utf-8") as f:
            f.write("# HYPER AGENT BIBLE\n\n## Section 1: Core Principles\n\nAlways ask for approval.\n\n## Section 2: Coding Standards\n\nUse Python 3.11+.\n\n## Section 3: Handling User Feedback\n\nListen carefully and adapt.")
    
    # Ingest the Bible
    print(f"📚 Ingesting {bible_path}...")
    memory.ingest_document(bible_path)
    
    # Query test
    test_query = "How should I handle user feedback?"
    print(f"\n❓ Query: {test_query}")
    
    relevant_context = memory.query_relevant_context(test_query, top_k=1)
    
    print("\n✅ Retrieved Context:")
    print("─" * 60)
    print(relevant_context)
    print("─" * 60)
    
    # Show token savings (approximate)
    with open(bible_path, "r", encoding="utf-8") as f:
        full_text = f.read()
        full_size = len(full_text)
    
    context_size = len(relevant_context)
    
    print("\n💰 Approximate Savings:")
    print(f"   Full Document: {full_size} chars")
    print(f"   RAG Context:   {context_size} chars")
    if full_size > 0:
        print(f"   Reduction:     {100 - (context_size / full_size * 100):.1f}%")

if __name__ == "__main__":
    try:
        asyncio.run(test_rag())
    except Exception as e:
        print(f"❌ Error: {e}")
