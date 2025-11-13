#!/usr/bin/env python3
"""Example demonstrating VectorStore usage for duplicate detection.

This script shows:
1. Creating a vector store
2. Adding documents with metadata
3. Searching for similar documents
4. Detecting duplicates and related content
"""

from pathlib import Path

from aris.storage.vector_store import VectorStore


def main() -> None:
    """Run vector store demonstration."""
    print("=" * 70)
    print("ARIS Vector Store Demonstration")
    print("=" * 70)

    # Create in-memory vector store
    print("\n1. Initializing vector store...")
    store = VectorStore(persist_dir=None)
    print("   ✓ Vector store created (in-memory)")

    # Add sample documents
    print("\n2. Adding sample documents...")
    documents = [
        {
            "id": "doc_001",
            "content": (
                "Machine learning is a subset of artificial intelligence that enables "
                "computer systems to learn from data and improve their performance without "
                "being explicitly programmed."
            ),
            "metadata": {"title": "ML Fundamentals", "topic": "AI"},
        },
        {
            "id": "doc_002",
            "content": (
                "Deep learning uses neural networks with multiple layers to automatically "
                "learn representations from data for tasks like classification and regression."
            ),
            "metadata": {"title": "Deep Learning Guide", "topic": "AI"},
        },
        {
            "id": "doc_003",
            "content": (
                "Machine learning is a subset of artificial intelligence that enables "
                "computer systems to learn from data without being explicitly programmed. "
                "It improves performance through experience."
            ),
            "metadata": {
                "title": "ML Fundamentals (Alternative)",
                "topic": "AI",
                "status": "draft",
            },
        },
        {
            "id": "doc_004",
            "content": (
                "Python is a high-level programming language known for its simplicity and "
                "readability. It has extensive libraries for web development, data science, "
                "and artificial intelligence."
            ),
            "metadata": {"title": "Python Guide", "topic": "Programming"},
        },
    ]

    for doc in documents:
        store.add_document(doc["id"], doc["content"], doc["metadata"])
        print(f"   ✓ Added {doc['id']}: {doc['metadata']['title']}")

    # Show statistics
    print("\n3. Vector store statistics:")
    stats = store.get_collection_stats()
    print(f"   Total documents: {stats['total_documents']}")

    # Demonstrate duplicate detection
    print("\n4. Duplicate Detection (threshold=0.85):")
    query_content = (
        "Machine learning is a subset of artificial intelligence that enables "
        "systems to learn from data."
    )
    print(f"   Query: {query_content[:60]}...")

    duplicates = store.search_similar(query_content, threshold=0.85, limit=10)
    print(f"   Found {len(duplicates)} potential duplicates:")
    for doc_id, score, metadata in duplicates:
        print(f"   - {doc_id}: {metadata.get('title', 'N/A')} (score: {score:.3f})")

    # Demonstrate related document search
    print("\n5. Related Documents Search (threshold=0.70):")
    related = store.search_similar(query_content, threshold=0.70, limit=10)
    print(f"   Found {len(related)} related documents:")
    for doc_id, score, metadata in related:
        print(f"   - {doc_id}: {metadata.get('title', 'N/A')} (score: {score:.3f})")

    # Demonstrate cross-domain search
    print("\n6. Cross-domain Search (AI -> Programming):")
    python_query = "Python programming language for data science"
    cross_domain = store.search_similar(python_query, threshold=0.50, limit=10)
    print(f"   Query: {python_query}")
    print(f"   Found {len(cross_domain)} results:")
    for doc_id, score, metadata in cross_domain:
        print(f"   - {doc_id}: {metadata.get('title', 'N/A')} (score: {score:.3f})")

    # Test update operation
    print("\n7. Testing Document Update:")
    updated_content = (
        "Machine learning fundamentals: "
        "ML is a subset of AI enabling systems to learn from data and adapt. "
        "It powers recommendation systems, computer vision, and NLP."
    )
    store.update_document("doc_001", updated_content)
    print("   ✓ Updated doc_001 with new content")

    # Retrieve and display document
    print("\n8. Retrieving Updated Document:")
    doc = store.get_document("doc_001")
    if doc:
        print(f"   ✓ Retrieved {doc['id']}")
        print(f"   Title: {doc['metadata'].get('title', 'N/A')}")
        print(f"   Content preview: {doc['content'][:80]}...")

    # Test delete operation
    print("\n9. Testing Document Deletion:")
    store.delete_document("doc_003")
    print("   ✓ Deleted doc_003")
    stats = store.get_collection_stats()
    print(f"   Remaining documents: {stats['total_documents']}")

    print("\n" + "=" * 70)
    print("Demonstration Complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()
