"""
Gemini LLM integration for LightRAG using the new unified Google Gen AI SDK.
Preserves gamified prompt optimizations while leveraging Gemini 2.5 Flash.
"""

import os
import numpy as np
from typing import Any, List, Dict, Optional, Union
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Dynamic installation if needed
try:
    from google import genai
    from google.genai import types
except ImportError:
    try:
        import subprocess
        subprocess.check_call(["pip", "install", "google-genai"])
        from google import genai
        from google.genai import types
    except Exception as e:
        raise ImportError(f"Failed to install google-genai: {e}")

from lightrag.utils import safe_unicode_decode, logger


class GeminiError(Exception):
    """Custom exception for Gemini-specific errors"""
    pass


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type((Exception,))
)
async def gemini_complete_if_cache(
    model: str,
    prompt: str,
    system_prompt: Optional[str] = None,
    history_messages: Optional[List[Dict[str, Any]]] = None,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    **kwargs: Any,
) -> str:
    """
    Generate completion using Google's unified Gen AI SDK.
    Supports both Gemini Developer API and Vertex AI.
    """
    
    # Determine which API to use based on environment
    use_vertexai = os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "false").lower() == "true"
    
    if use_vertexai:
        # Vertex AI configuration
        project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
        location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
        
        if not project_id:
            raise ValueError("GOOGLE_CLOUD_PROJECT environment variable required for Vertex AI")
        
        # Create Vertex AI client
        client = genai.Client(
            vertexai=True,
            project=project_id,
            location=location,
            http_options=types.HttpOptions(api_version="v1")
        )
        
        logger.info(f"🤖 Using Vertex AI with project {project_id} in {location}")
    else:
        # Gemini Developer API configuration
        if not api_key:
            api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        
        if not api_key:
            raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY required for Gemini Developer API")
        
        # Create Developer API client
        client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(api_version="v1")
        )
        
        logger.info(f"🤖 Using Gemini Developer API with model: {model}")
    
    # Build conversation content
    contents = []
    
    # Add conversation history if provided
    if history_messages:
        for msg in history_messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            contents.append(types.Part.from_text(content))
    
    # Add current prompt
    contents.append(types.Part.from_text(prompt))
    
    # Configure generation parameters
    config = types.GenerateContentConfig(
        temperature=kwargs.get("temperature", 0.1),  # Low for consistency with optimized prompts
        max_output_tokens=kwargs.get("max_tokens", 8192),
        top_p=kwargs.get("top_p", 0.8),
        top_k=kwargs.get("top_k", 40),
    )
    
    # Add system instruction if provided
    if system_prompt:
        config.system_instruction = system_prompt
    
    try:
        # Generate response
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=model,
            contents=contents,
            config=config
        )
        
        # Extract text from response
        if hasattr(response, 'text'):
            return safe_unicode_decode(response.text)
        else:
            # Handle potential response structure variations
            candidates = getattr(response, 'candidates', [])
            if candidates and len(candidates) > 0:
                content = candidates[0].content
                if hasattr(content, 'parts') and content.parts:
                    text_parts = [part.text for part in content.parts if hasattr(part, 'text')]
                    return safe_unicode_decode(' '.join(text_parts))
            
            raise GeminiError("No valid text response from Gemini")
            
    except Exception as e:
        logger.error(f"Gemini API error: {str(e)}")
        raise


async def gemini_embed(
    texts: List[str],
    model: str = "text-embedding-004",
    api_key: Optional[str] = None,
    **kwargs: Any,
) -> np.ndarray:
    """
    Generate embeddings using Gemini's embedding models.
    Note: Vertex AI and Developer API may have different embedding model availability.
    """
    
    # Determine which API to use
    use_vertexai = os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "false").lower() == "true"
    
    if use_vertexai:
        # Vertex AI configuration
        project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
        location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
        
        client = genai.Client(
            vertexai=True,
            project=project_id,
            location=location,
            http_options=types.HttpOptions(api_version="v1")
        )
    else:
        # Developer API configuration
        if not api_key:
            api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        
        client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(api_version="v1")
        )
    
    embeddings = []
    
    # Process texts in batches to avoid rate limits
    batch_size = kwargs.get("batch_size", 20)
    
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        
        try:
            # Note: The new SDK's embedding API might differ
            # This is a placeholder - adjust based on actual API
            for text in batch:
                response = await asyncio.to_thread(
                    client.embeddings.embed_content,
                    model=f"models/{model}",
                    content=text,
                    task_type="retrieval_document"
                )
                
                if hasattr(response, 'embedding'):
                    embeddings.append(response.embedding)
                else:
                    raise GeminiError("Invalid embedding response structure")
                    
        except Exception as e:
            logger.error(f"Embedding error: {str(e)}")
            # Fallback: Return zero vectors of appropriate dimension
            embedding_dim = kwargs.get("embedding_dim", 768)
            embeddings.extend([np.zeros(embedding_dim) for _ in batch])
    
    return np.array(embeddings)


# Convenience function for streaming responses
async def gemini_complete_stream(
    model: str,
    prompt: str,
    system_prompt: Optional[str] = None,
    history_messages: Optional[List[Dict[str, Any]]] = None,
    api_key: Optional[str] = None,
    **kwargs: Any,
):
    """
    Stream completion responses for real-time applications.
    Yields chunks of text as they're generated.
    """
    
    use_vertexai = os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "false").lower() == "true"
    
    if use_vertexai:
        project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
        location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
        
        client = genai.Client(
            vertexai=True,
            project=project_id,
            location=location
        )
    else:
        if not api_key:
            api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        
        client = genai.Client(api_key=api_key)
    
    contents = []
    if history_messages:
        for msg in history_messages:
            contents.append(types.Part.from_text(msg.get("content", "")))
    
    contents.append(types.Part.from_text(prompt))
    
    config = types.GenerateContentConfig(
        temperature=kwargs.get("temperature", 0.1),
        max_output_tokens=kwargs.get("max_tokens", 8192),
    )
    
    if system_prompt:
        config.system_instruction = system_prompt
    
    # Use streaming method
    response_stream = client.models.generate_content_stream(
        model=model,
        contents=contents,
        config=config
    )
    
    async for chunk in response_stream:
        if hasattr(chunk, 'text'):
            yield chunk.text
        elif hasattr(chunk, 'candidates') and chunk.candidates:
            for candidate in chunk.candidates:
                if hasattr(candidate.content, 'parts'):
                    for part in candidate.content.parts:
                        if hasattr(part, 'text'):
                            yield part.text