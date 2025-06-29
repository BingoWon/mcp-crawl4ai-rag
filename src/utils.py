"""
Utility functions for the Crawl4AI MCP server.
"""
import os
import concurrent.futures
from typing import List, Dict, Any, Optional, Tuple
import json
from urllib.parse import urlparse
import openai
import requests
import time
import asyncio

# Import the modern PostgreSQL client
try:
    from .postgres_client import get_postgres_client, PostgreSQLClient
except ImportError:
    from postgres_client import get_postgres_client, PostgreSQLClient

# LLM client for chat completions
llm_client = openai.OpenAI(
    api_key=os.getenv("LLM_API_KEY"),
    base_url=os.getenv("LLM_BASE_URL")
)

# LLM configuration
LLM_MODEL = os.getenv("LLM_MODEL")

# Import embedding provider
try:
    from .embedding_provider import create_embedder
    EMBEDDING_AVAILABLE = True
except ImportError:
    try:
        from embedding_provider import create_embedder
        EMBEDDING_AVAILABLE = True
    except ImportError:
        EMBEDDING_AVAILABLE = False
        print("⚠️  Embedding provider not available. Install transformers and torch.")

# Global embedder instance (lazy initialization)
_embedder = None

def get_embedder():
    """Get or create the global embedding provider instance."""
    global _embedder
    if _embedder is None and EMBEDDING_AVAILABLE:
        try:
            _embedder = create_embedder()
        except Exception as e:
            print(f"❌ Failed to initialize embedding provider: {e}")
            _embedder = None
    return _embedder

async def get_database_client() -> PostgreSQLClient:
    """
    Get a PostgreSQL client instance.

    Returns:
        PostgreSQL client instance
    """
    return await get_postgres_client()

def _create_embeddings_qwen3(texts: List[str]) -> List[List[float]]:
    """
    Create embeddings using Qwen3-Embedding-4B.

    Args:
        texts: List of texts to create embeddings for

    Returns:
        List of embeddings (each embedding is a list of floats)
    """
    embedder = get_embedder()
    if embedder is None:
        raise RuntimeError("Qwen3-Embedding not available")

    try:
        # Encode as documents (no instruction)
        embeddings_tensor = embedder.encode(texts, is_query=False)
        return embeddings_tensor.cpu().tolist()
    except Exception as e:
        print(f"❌ Error creating embeddings: {e}")
        raise

def create_embeddings_batch(texts: List[str]) -> List[List[float]]:
    """
    Create embeddings for multiple texts using Qwen3-Embedding-4B.

    Args:
        texts: List of texts to create embeddings for

    Returns:
        List of embeddings (each embedding is a list of floats)
    """
    if not texts:
        return []

    max_retries = 3
    retry_delay = 1.0

    for retry in range(max_retries):
        try:
            return _create_embeddings_qwen3(texts)
        except Exception as e:
            if retry < max_retries - 1:
                print(f"Error creating batch embeddings (attempt {retry + 1}/{max_retries}): {e}")
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2
            else:
                print(f"Failed to create batch embeddings after {max_retries} attempts: {e}")
                # Try individual embeddings as fallback
                embeddings = []
                for i, text in enumerate(texts):
                    try:
                        individual_embeddings = _create_embeddings_qwen3([text])
                        embeddings.append(individual_embeddings[0])
                    except Exception:
                        print(f"Failed to create embedding for text {i}")
                        # Use default embedding size for Qwen3-Embedding-4B
                        embeddings.append([0.0] * 2560)
                return embeddings

def create_embedding(text: str) -> List[float]:
    """
    Create an embedding for a single text using Qwen3-Embedding-4B.

    Args:
        text: Text to create an embedding for

    Returns:
        List of floats representing the embedding
    """
    try:
        embeddings = create_embeddings_batch([text])
        return embeddings[0] if embeddings else [0.0] * 2560
    except Exception as e:
        print(f"Error creating embedding: {e}")
        # Return empty embedding if there's an error (Qwen3-Embedding-4B default size)
        return [0.0] * 2560

def generate_contextual_embedding(full_document: str, chunk: str) -> Tuple[str, bool]:
    """
    Generate contextual information for a chunk within a document to improve retrieval.

    Args:
        full_document: The complete document text
        chunk: The specific chunk of text to generate context for

    Returns:
        Tuple containing:
        - The contextual text that situates the chunk within the document
        - Boolean indicating if contextual embedding was performed
    """
    
    try:
        # Create the prompt for generating contextual information
        prompt = f"""<document> 
{full_document[:25000]} 
</document>
Here is the chunk we want to situate within the whole document 
<chunk> 
{chunk}
</chunk> 
Please give a short succinct context to situate this chunk within the overall document for the purposes of improving search retrieval of the chunk. Answer only with the succinct context and nothing else."""

        # Call the LLM API to generate contextual information
        response = llm_client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that provides concise contextual information."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=200
        )
        
        # Extract the generated context
        context = response.choices[0].message.content.strip()
        
        # Combine the context with the original chunk
        contextual_text = f"{context}\n---\n{chunk}"
        
        return contextual_text, True
    
    except Exception as e:
        print(f"Error generating contextual embedding: {e}. Using original chunk instead.")
        return chunk, False

def process_chunk_with_context(args):
    """
    Process a single chunk with contextual embedding.
    This function is designed to be used with concurrent.futures.

    Args:
        args: Tuple containing (url, content, full_document)

    Returns:
        Tuple containing:
        - The contextual text that situates the chunk within the document
        - Boolean indicating if contextual embedding was performed
    """
    _, content, full_document = args
    return generate_contextual_embedding(full_document, content)

async def add_documents_to_database(
    client: PostgreSQLClient,
    urls: List[str],
    chunk_numbers: List[int],
    contents: List[str],
    metadatas: List[Dict[str, Any]],
    url_to_full_document: Dict[str, str],
    batch_size: int = 20
) -> None:
    """
    Add documents to the crawled_pages table in batches.
    Deletes existing records with the same URLs before inserting to prevent duplicates.

    Args:
        client: PostgreSQL client
        urls: List of URLs
        chunk_numbers: List of chunk numbers
        contents: List of document contents
        metadatas: List of document metadata
        url_to_full_document: Dictionary mapping URLs to their full document content
        batch_size: Size of each batch for insertion
    """
    # Get unique URLs to delete existing records
    unique_urls = list(set(urls))

    # Delete existing records for these URLs
    if unique_urls:
        try:
            # Use PostgreSQL ANY operator for efficient batch deletion
            placeholders = ', '.join(['$' + str(i+1) for i in range(len(unique_urls))])
            await client.execute_command(
                f"DELETE FROM crawled_pages WHERE url = ANY(ARRAY[{placeholders}])",
                *unique_urls
            )
        except Exception as e:
            print(f"Error deleting existing records: {e}")
    
    # Check if MODEL_CHOICE is set for contextual embeddings
    use_contextual_embeddings = os.getenv("USE_CONTEXTUAL_EMBEDDINGS", "false") == "true"
    print(f"\n\nUse contextual embeddings: {use_contextual_embeddings}\n\n")
    
    # Process in batches to avoid memory issues
    for i in range(0, len(contents), batch_size):
        batch_end = min(i + batch_size, len(contents))
        
        # Get batch slices
        batch_urls = urls[i:batch_end]
        batch_chunk_numbers = chunk_numbers[i:batch_end]
        batch_contents = contents[i:batch_end]
        batch_metadatas = metadatas[i:batch_end]
        
        # Apply contextual embedding to each chunk if MODEL_CHOICE is set
        if use_contextual_embeddings:
            # Prepare arguments for parallel processing
            process_args = []
            for j, content in enumerate(batch_contents):
                url = batch_urls[j]
                full_document = url_to_full_document.get(url, "")
                process_args.append((url, content, full_document))
            
            # Process in parallel using ThreadPoolExecutor
            contextual_contents = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                # Submit all tasks and collect results
                future_to_idx = {executor.submit(process_chunk_with_context, arg): idx 
                                for idx, arg in enumerate(process_args)}
                
                # Process results as they complete
                for future in concurrent.futures.as_completed(future_to_idx):
                    idx = future_to_idx[future]
                    try:
                        result, success = future.result()
                        contextual_contents.append(result)
                        if success:
                            batch_metadatas[idx]["contextual_embedding"] = True
                    except Exception as e:
                        print(f"Error processing chunk {idx}: {e}")
                        # Use original content as fallback
                        contextual_contents.append(batch_contents[idx])
            
            # Sort results back into original order if needed
            if len(contextual_contents) != len(batch_contents):
                print(f"Warning: Expected {len(batch_contents)} results but got {len(contextual_contents)}")
                # Use original contents as fallback
                contextual_contents = batch_contents
        else:
            # If not using contextual embeddings, use original contents
            contextual_contents = batch_contents
        
        # Create embeddings for the entire batch at once
        batch_embeddings = create_embeddings_batch(contextual_contents)
        
        batch_data = []
        for j in range(len(contextual_contents)):
            # Extract metadata fields
            chunk_size = len(contextual_contents[j])
            
            # Extract source_id from URL
            parsed_url = urlparse(batch_urls[j])
            source_id = parsed_url.netloc or parsed_url.path
            
            # Prepare data for insertion
            data = {
                "url": batch_urls[j],
                "chunk_number": batch_chunk_numbers[j],
                "content": contextual_contents[j],  # Store original content
                "metadata": {
                    "chunk_size": chunk_size,
                    **batch_metadatas[j]
                },
                "source_id": source_id,  # Add source_id field
                "embedding": batch_embeddings[j]  # Use embedding from contextual content
            }
            
            batch_data.append(data)
        
        # Insert batch into PostgreSQL
        try:
            await client.insert_batch("crawled_pages", batch_data)
        except Exception as e:
            print(f"Error inserting batch: {e}")
            # Try inserting records individually as fallback
            successful_inserts = 0
            for record in batch_data:
                try:
                    await client.insert_batch("crawled_pages", [record])
                    successful_inserts += 1
                except Exception as individual_error:
                    print(f"Failed to insert individual record for URL {record['url']}: {individual_error}")

            if successful_inserts > 0:
                print(f"Successfully inserted {successful_inserts}/{len(batch_data)} records individually")

async def _search_documents_async(
    client: PostgreSQLClient,
    query: str,
    match_count: int = 10,
    filter_metadata: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Search for documents using vector similarity.

    Args:
        client: PostgreSQL client
        query: Query text
        match_count: Maximum number of results to return
        filter_metadata: Optional metadata filter

    Returns:
        List of matching documents
    """
    # Create embedding for the query
    query_embedding = create_embedding(query)

    # Execute the search using the match_crawled_pages function
    try:
        # Prepare parameters for the function call
        params = [query_embedding, match_count]

        # Add filter parameters if provided
        if filter_metadata:
            params.extend([json.dumps(filter_metadata), None])
        else:
            params.extend([json.dumps({}), None])

        result = await client.call_function('match_crawled_pages', *params)
        return result
    except Exception as e:
        print(f"Error searching documents: {e}")
        return []


def extract_code_blocks(markdown_content: str, min_length: int = 1000) -> List[Dict[str, Any]]:
    """
    Extract code blocks from markdown content along with context.
    
    Args:
        markdown_content: The markdown content to extract code blocks from
        min_length: Minimum length of code blocks to extract (default: 1000 characters)
        
    Returns:
        List of dictionaries containing code blocks and their context
    """
    code_blocks = []
    
    # Skip if content starts with triple backticks (edge case for files wrapped in backticks)
    content = markdown_content.strip()
    start_offset = 0
    if content.startswith('```'):
        # Skip the first triple backticks
        start_offset = 3
        print("Skipping initial triple backticks")
    
    # Find all occurrences of triple backticks
    backtick_positions = []
    pos = start_offset
    while True:
        pos = markdown_content.find('```', pos)
        if pos == -1:
            break
        backtick_positions.append(pos)
        pos += 3
    
    # Process pairs of backticks
    i = 0
    while i < len(backtick_positions) - 1:
        start_pos = backtick_positions[i]
        end_pos = backtick_positions[i + 1]
        
        # Extract the content between backticks
        code_section = markdown_content[start_pos+3:end_pos]
        
        # Check if there's a language specifier on the first line
        lines = code_section.split('\n', 1)
        if len(lines) > 1:
            # Check if first line is a language specifier (no spaces, common language names)
            first_line = lines[0].strip()
            if first_line and ' ' not in first_line and len(first_line) < 20:
                language = first_line
                code_content = lines[1].strip() if len(lines) > 1 else ""
            else:
                language = ""
                code_content = code_section.strip()
        else:
            language = ""
            code_content = code_section.strip()
        
        # Skip if code block is too short
        if len(code_content) < min_length:
            i += 2  # Move to next pair
            continue
        
        # Extract context before (1000 chars)
        context_start = max(0, start_pos - 1000)
        context_before = markdown_content[context_start:start_pos].strip()
        
        # Extract context after (1000 chars)
        context_end = min(len(markdown_content), end_pos + 3 + 1000)
        context_after = markdown_content[end_pos + 3:context_end].strip()
        
        code_blocks.append({
            'code': code_content,
            'language': language,
            'context_before': context_before,
            'context_after': context_after,
            'full_context': f"{context_before}\n\n{code_content}\n\n{context_after}"
        })
        
        # Move to next pair (skip the closing backtick we just processed)
        i += 2
    
    return code_blocks


def generate_code_example_summary(code: str, context_before: str, context_after: str) -> str:
    """
    Generate a summary for a code example using its surrounding context.

    Args:
        code: The code example
        context_before: Context before the code
        context_after: Context after the code

    Returns:
        A summary of what the code example demonstrates
    """
    
    # Create the prompt
    prompt = f"""<context_before>
{context_before[-500:] if len(context_before) > 500 else context_before}
</context_before>

<code_example>
{code[:1500] if len(code) > 1500 else code}
</code_example>

<context_after>
{context_after[:500] if len(context_after) > 500 else context_after}
</context_after>

Based on the code example and its surrounding context, provide a concise summary (2-3 sentences) that describes what this code example demonstrates and its purpose. Focus on the practical application and key concepts illustrated.
"""
    
    try:
        response = llm_client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that provides concise code example summaries."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=100
        )
        
        return response.choices[0].message.content.strip()
    
    except Exception as e:
        print(f"Error generating code example summary: {e}")
        return "Code example for demonstration purposes."


async def add_code_examples_to_database(
    client: PostgreSQLClient,
    urls: List[str],
    chunk_numbers: List[int],
    code_examples: List[str],
    summaries: List[str],
    metadatas: List[Dict[str, Any]],
    batch_size: int = 20
):
    """
    Add code examples to the code_examples table in batches.

    Args:
        client: PostgreSQL client
        urls: List of URLs
        chunk_numbers: List of chunk numbers
        code_examples: List of code example contents
        summaries: List of code example summaries
        metadatas: List of metadata dictionaries
        batch_size: Size of each batch for insertion
    """
    if not urls:
        return
        
    # Delete existing records for these URLs
    unique_urls = list(set(urls))
    if unique_urls:
        try:
            placeholders = ', '.join(['$' + str(i+1) for i in range(len(unique_urls))])
            await client.execute_command(
                f"DELETE FROM code_examples WHERE url = ANY(ARRAY[{placeholders}])",
                *unique_urls
            )
        except Exception as e:
            print(f"Error deleting existing code examples: {e}")
    
    # Process in batches
    total_items = len(urls)
    for i in range(0, total_items, batch_size):
        batch_end = min(i + batch_size, total_items)
        batch_texts = []
        
        # Create combined texts for embedding (code + summary)
        for j in range(i, batch_end):
            combined_text = f"{code_examples[j]}\n\nSummary: {summaries[j]}"
            batch_texts.append(combined_text)
        
        # Create embeddings for the batch
        embeddings = create_embeddings_batch(batch_texts)
        
        # Check if embeddings are valid (not all zeros)
        valid_embeddings = []
        for embedding in embeddings:
            if embedding and not all(v == 0.0 for v in embedding):
                valid_embeddings.append(embedding)
            else:
                print("Warning: Zero or invalid embedding detected, creating new one...")
                # Try to create a single embedding as fallback
                single_embedding = create_embedding(batch_texts[len(valid_embeddings)])
                valid_embeddings.append(single_embedding)
        
        # Prepare batch data
        batch_data = []
        for j, embedding in enumerate(valid_embeddings):
            idx = i + j
            
            # Extract source_id from URL
            parsed_url = urlparse(urls[idx])
            source_id = parsed_url.netloc or parsed_url.path
            
            batch_data.append({
                'url': urls[idx],
                'chunk_number': chunk_numbers[idx],
                'content': code_examples[idx],
                'summary': summaries[idx],
                'metadata': metadatas[idx],  # Store as JSON object, not string
                'source_id': source_id,
                'embedding': embedding
            })
        
        # Insert batch into PostgreSQL
        try:
            await client.insert_batch("code_examples", batch_data)
            print(f"Inserted batch {i//batch_size + 1} of {(total_items + batch_size - 1)//batch_size} code examples")
        except Exception as e:
            print(f"Error inserting batch: {e}")
            # Try inserting records individually as fallback
            successful_inserts = 0
            for record in batch_data:
                try:
                    await client.insert_batch("code_examples", [record])
                    successful_inserts += 1
                except Exception as individual_error:
                    print(f"Failed to insert individual record for URL {record['url']}: {individual_error}")

            if successful_inserts > 0:
                print(f"Successfully inserted {successful_inserts}/{len(batch_data)} records individually")


async def update_source_info(client: PostgreSQLClient, source_id: str, summary: str, word_count: int):
    """
    Update or insert source information in the sources table.

    Args:
        client: PostgreSQL client
        source_id: The source ID (domain)
        summary: Summary of the source
        word_count: Total word count for the source
    """
    try:
        # Use upsert to insert or update
        record = {
            'source_id': source_id,
            'summary': summary,
            'total_word_count': word_count
        }
        await client.upsert_record('sources', record, ['source_id'])
        print(f"Updated/created source: {source_id}")
    except Exception as e:
        print(f"Error updating source info: {e}")


def extract_source_summary(source_id: str, content: str, max_length: int = 500) -> str:
    """
    Extract a summary for a source from its content using an LLM.
    
    This function uses the OpenAI API to generate a concise summary of the source content.
    
    Args:
        source_id: The source ID (domain)
        content: The content to extract a summary from
        max_length: Maximum length of the summary
        
    Returns:
        A summary string
    """
    # Default summary if we can't extract anything meaningful
    default_summary = f"Content from {source_id}"
    
    if not content or len(content.strip()) == 0:
        return default_summary
    
    # Limit content length to avoid token limits
    truncated_content = content[:25000] if len(content) > 25000 else content
    
    # Create the prompt for generating the summary
    prompt = f"""<source_content>
{truncated_content}
</source_content>

The above content is from the documentation for '{source_id}'. Please provide a concise summary (3-5 sentences) that describes what this library/tool/framework is about. The summary should help understand what the library/tool/framework accomplishes and the purpose.
"""
    
    try:
        # Call the LLM API to generate the summary
        response = llm_client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that provides concise library/tool/framework summaries."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=150
        )
        
        # Extract the generated summary
        summary = response.choices[0].message.content.strip()
        
        # Ensure the summary is not too long
        if len(summary) > max_length:
            summary = summary[:max_length] + "..."
            
        return summary
    
    except Exception as e:
        print(f"Error generating summary with LLM for {source_id}: {e}. Using default summary.")
        return default_summary


async def _search_code_examples_async(
    client: PostgreSQLClient,
    query: str,
    match_count: int = 10,
    filter_metadata: Optional[Dict[str, Any]] = None,
    source_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Search for code examples using vector similarity.

    Args:
        client: PostgreSQL client
        query: Query text
        match_count: Maximum number of results to return
        filter_metadata: Optional metadata filter
        source_id: Optional source ID to filter results

    Returns:
        List of matching code examples
    """
    # Create a more descriptive query for better embedding match
    enhanced_query = f"Code example for {query}\n\nSummary: Example code showing {query}"

    # Create embedding for the enhanced query
    query_embedding = create_embedding(enhanced_query)

    # Execute the search using the match_code_examples function
    try:
        # Prepare parameters for the function call
        params = [query_embedding, match_count]

        # Add filter parameters
        if filter_metadata:
            params.extend([json.dumps(filter_metadata), source_id])
        else:
            params.extend([json.dumps({}), source_id])

        result = await client.call_function('match_code_examples', *params)
        return result
    except Exception as e:
        print(f"Error searching code examples: {e}")
        return []


# Synchronous wrapper functions for backward compatibility
def add_documents_to_supabase(client, urls, chunk_numbers, contents, metadatas, url_to_full_document, batch_size=20):
    """Synchronous wrapper for add_documents_to_database."""
    return asyncio.run(add_documents_to_database(client, urls, chunk_numbers, contents, metadatas, url_to_full_document, batch_size))

def search_documents(client, query, match_count=10, filter_metadata=None):
    """Synchronous wrapper for search_documents."""
    return asyncio.run(_search_documents_async(client, query, match_count, filter_metadata))

def add_code_examples_to_supabase(client, urls, chunk_numbers, code_examples, summaries, metadatas, batch_size=20):
    """Synchronous wrapper for add_code_examples_to_database."""
    return asyncio.run(add_code_examples_to_database(client, urls, chunk_numbers, code_examples, summaries, metadatas, batch_size))

def search_code_examples(client, query, match_count=10, filter_metadata=None, source_id=None):
    """Synchronous wrapper for search_code_examples."""
    return asyncio.run(_search_code_examples_async(client, query, match_count, filter_metadata, source_id))

def get_supabase_client():
    """Synchronous wrapper to get database client."""
    return asyncio.run(get_database_client())