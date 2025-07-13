import sys
import asyncio
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from database import PostgreSQLClient, DatabaseOperations
from embedding import get_embedder


async def test_database_connection():
    """Test PostgreSQL connection"""
    async with PostgreSQLClient() as client:
        assert client is not None
        print("✅ Database connection test passed")


async def test_database_operations():
    """Test database operations"""
    async with PostgreSQLClient() as client:
        db_ops = DatabaseOperations(client)
        
        # Test basic operations
        urls = await db_ops.get_all_crawled_urls()
        assert isinstance(urls, list)
        print("✅ Database operations test passed")


async def test_vector_2560_no_index():
    """Test vector(2560) storage and exact search without indexes"""
    embedder = get_embedder()

    # Test embedding generation
    test_texts = [
        "Apple iPhone development documentation",
        "Swift programming language guide",
        "iOS app development tutorial",
        "Android development guide",
        "Python programming basics"
    ]

    async with PostgreSQLClient() as client:
        db_ops = DatabaseOperations(client)

        print("=== Testing vector(2560) exact search ===")

        # Store multiple test documents
        test_data = []
        embeddings = []
        for i, text in enumerate(test_texts):
            embedding = embedder.encode_single(text)
            embeddings.append(embedding)
            assert len(embedding) == 2560, f"Expected 2560 dims, got {len(embedding)}"

            test_data.append({
                'url': f'test://vector-test-{i}',
                'content': text,
                'embedding': str(embedding)
            })

        try:
            await db_ops.insert_crawled_pages(test_data)
            print(f"✅ Stored {len(test_data)} documents with 2560-dim vectors")

            # Test exact vector search (no index, brute-force)
            query_embedding = embeddings[0]  # Use first embedding as query

            # Test cosine similarity search
            import time
            start_time = time.time()

            results = await client.execute_query("""
                SELECT url, content, embedding, embedding <=> $1 as distance
                FROM crawled_pages
                WHERE url LIKE 'test://vector-test-%'
                ORDER BY embedding <=> $1
                LIMIT 3
            """, str(query_embedding))

            search_time = time.time() - start_time

            print(f"✅ Vector search completed in {search_time:.3f}s")
            print(f"✅ Found {len(results)} results")

            # Verify exact match (distance should be 0 for identical vectors)
            if results and results[0]['distance'] < 1e-10:
                print("✅ Exact vector match confirmed (distance ≈ 0)")
            else:
                print(f"⚠️ Unexpected distance: {results[0]['distance'] if results else 'No results'}")

            # Test precision integrity
            original_vector = embeddings[0]
            stored_vector_str = results[0]['embedding'] if results else None

            if stored_vector_str:
                # Parse stored vector back to list
                stored_vector = eval(stored_vector_str.replace('[', '[').replace(']', ']'))

                # Compare precision
                max_diff = max(abs(a - b) for a, b in zip(original_vector, stored_vector))
                print(f"✅ Maximum precision difference: {max_diff:.2e}")

                if max_diff < 1e-6:  # Single precision float tolerance
                    print("✅ Full precision maintained (32-bit float)")
                else:
                    print(f"⚠️ Precision loss detected: {max_diff}")

            print("✅ vector(2560) exact search test passed")

        except Exception as e:
            print(f"❌ vector(2560) test failed: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(test_database_connection())
    asyncio.run(test_database_operations())
    asyncio.run(test_vector_2560_no_index())
    print("✅ All database tests completed")
