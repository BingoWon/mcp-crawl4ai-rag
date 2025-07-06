"""
Crawler Helper Functions
爬虫辅助函数模块

Contains utility functions for content processing, embedding generation, etc.
包含内容处理、嵌入生成等实用函数。
"""

from typing import List, Optional
from urllib.parse import urldefrag

# Import unified embedding module
try:
    import sys
    from pathlib import Path
    src_path = Path(__file__).parent.parent
    sys.path.insert(0, str(src_path))
    from embedding import create_embeddings_batch
    EMBEDDING_AVAILABLE = True
except ImportError:
    EMBEDDING_AVAILABLE = False
    print("⚠️  Unified embedding module not available")

# Import LLM for summaries
try:
    import openai
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False
    print("⚠️  OpenAI not available for summaries")


def smart_chunk_markdown(text: str, chunk_size: int = 5000) -> List[str]:
    """Split text into chunks, respecting code blocks and paragraphs."""
    chunks = []
    start = 0
    text_length = len(text)
    
    while start < text_length:
        end = min(start + chunk_size, text_length)
        
        # If we're not at the end of the text, try to find a good break point
        if end < text_length:
            # Look for paragraph breaks first
            last_double_newline = text.rfind('\n\n', start, end)
            if last_double_newline > start:
                end = last_double_newline + 2
            else:
                # Look for single newlines
                last_newline = text.rfind('\n', start, end)
                if last_newline > start:
                    end = last_newline + 1
                else:
                    # Look for sentence endings
                    last_sentence = max(
                        text.rfind('. ', start, end),
                        text.rfind('! ', start, end),
                        text.rfind('? ', start, end)
                    )
                    if last_sentence > start:
                        end = last_sentence + 2
        
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        start = end
    
    return chunks


def normalize_url(url: str) -> str:
    """Normalize URL by removing fragments and trailing slashes."""
    normalized, _ = urldefrag(url)
    return normalized.rstrip('/')


def extract_source_summary(source_id: str, content: str, max_length: int = 500) -> str:
    """Extract or generate a summary for a source."""
    if not LLM_AVAILABLE:
        return f"Content from {source_id}"
    
    # Truncate content for summary generation
    truncated_content = content[:5000] if len(content) > 5000 else content
    
    try:
        client = openai.OpenAI()
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "user",
                    "content": f"""<source_content>
{truncated_content}
</source_content>

The above content is from the documentation for '{source_id}'. Please provide a concise summary (3-5 sentences) that describes what this library/tool/framework is about."""
                }
            ],
            max_tokens=200,
            temperature=0.3
        )
        
        summary = response.choices[0].message.content.strip()
        
        # Ensure summary doesn't exceed max_length
        if len(summary) > max_length:
            summary = summary[:max_length-3] + "..."
            
        return summary
        
    except Exception as e:
        print(f"⚠️  Failed to generate summary for {source_id}: {e}")
        return f"Content from {source_id}"


def create_embeddings_safe(contents: List[str]) -> List[Optional[List[float]]]:
    """Safely create embeddings with fallback."""
    if EMBEDDING_AVAILABLE:
        try:
            return create_embeddings_batch(contents)
        except Exception as e:
            print(f"⚠️  Failed to create embeddings: {e}")
            return [None] * len(contents)
    else:
        return [None] * len(contents)


def is_apple_documentation(url: str) -> bool:
    """Check if URL is Apple developer documentation."""
    return 'developer.apple.com/documentation/' in url


def is_sitemap(url: str) -> bool:
    """Check if URL is a sitemap."""
    from urllib.parse import urlparse
    return url.endswith('sitemap.xml') or 'sitemap' in urlparse(url).path


def is_txt(url: str) -> bool:
    """Check if URL is a text file."""
    return url.endswith('.txt')


async def is_url_already_crawled(db_operations, url: str) -> bool:
    """Check if URL is already crawled in the database."""
    try:
        return await db_operations.url_exists(url)
    except Exception:
        return False
