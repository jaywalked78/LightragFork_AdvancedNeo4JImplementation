"""
This module contains all query-related routes for the LightRAG API.
"""

import json
import logging
import time
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from lightrag.base import QueryParam
from ..utils_api import get_combined_auth_dependency
from pydantic import BaseModel, Field, field_validator
from lightrag.api_query_logger import get_api_query_logger

from ascii_colors import trace_exception

router = APIRouter(tags=["query"])


class QueryRequest(BaseModel):
    query: str = Field(
        min_length=1,
        description="The query text",
    )

    mode: Literal["local", "global", "hybrid", "naive", "mix", "bypass"] = Field(
        default="hybrid",
        description="Query mode",
    )

    only_need_context: Optional[bool] = Field(
        default=None,
        description="If True, only returns the retrieved context without generating a response.",
    )

    only_need_prompt: Optional[bool] = Field(
        default=None,
        description="If True, only returns the generated prompt without producing a response.",
    )

    response_type: Optional[str] = Field(
        min_length=1,
        default=None,
        description="Defines the response format. Examples: 'Multiple Paragraphs', 'Single Paragraph', 'Bullet Points'.",
    )

    top_k: Optional[int] = Field(
        ge=1,
        default=None,
        description="Number of top items to retrieve. Represents entities in 'local' mode and relationships in 'global' mode.",
    )

    max_token_for_text_unit: Optional[int] = Field(
        gt=1,
        default=None,
        description="Maximum number of tokens allowed for each retrieved text chunk.",
    )

    max_token_for_global_context: Optional[int] = Field(
        gt=1,
        default=None,
        description="Maximum number of tokens allocated for relationship descriptions in global retrieval.",
    )

    max_token_for_local_context: Optional[int] = Field(
        gt=1,
        default=None,
        description="Maximum number of tokens allocated for entity descriptions in local retrieval.",
    )

    conversation_history: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Stores past conversation history to maintain context. Format: [{'role': 'user/assistant', 'content': 'message'}].",
    )

    history_turns: Optional[int] = Field(
        ge=0,
        default=None,
        description="Number of complete conversation turns (user-assistant pairs) to consider in the response context.",
    )

    ids: list[str] | None = Field(
        default=None, description="List of ids to filter the results."
    )

    user_prompt: Optional[str] = Field(
        default=None,
        description="User-provided prompt for the query. If provided, this will be used instead of the default value from prompt template.",
    )

    @field_validator("query", mode="after")
    @classmethod
    def query_strip_after(cls, query: str) -> str:
        return query.strip()

    @field_validator("conversation_history", mode="after")
    @classmethod
    def conversation_history_role_check(
        cls, conversation_history: List[Dict[str, Any]] | None
    ) -> List[Dict[str, Any]] | None:
        if conversation_history is None:
            return None
        for msg in conversation_history:
            if "role" not in msg or msg["role"] not in {"user", "assistant"}:
                raise ValueError(
                    "Each message must have a 'role' key with value 'user' or 'assistant'."
                )
        return conversation_history

    def to_query_params(self, is_stream: bool) -> "QueryParam":
        """Converts a QueryRequest instance into a QueryParam instance."""
        # Use Pydantic's `.model_dump(exclude_none=True)` to remove None values automatically
        request_data = self.model_dump(exclude_none=True, exclude={"query"})

        # Ensure `mode` and `stream` are set explicitly
        param = QueryParam(**request_data)
        param.stream = is_stream
        return param


class QueryResponse(BaseModel):
    response: str = Field(
        description="The generated response",
    )


def create_query_routes(rag, api_key: Optional[str] = None, top_k: int = 60):
    combined_auth = get_combined_auth_dependency(api_key)

    @router.post(
        "/query", response_model=QueryResponse, dependencies=[Depends(combined_auth)]
    )
    async def query_text(request: QueryRequest):
        """
        Handle a POST request at the /query endpoint to process user queries using RAG capabilities.

        Parameters:
            request (QueryRequest): The request object containing the query parameters.
        Returns:
            QueryResponse: A Pydantic model containing the result of the query processing.
                       If a string is returned (e.g., cache hit), it's directly returned.
                       Otherwise, an async generator may be used to build the response.

        Raises:
            HTTPException: Raised when an error occurs during the request handling process,
                       with status code 500 and detail containing the exception message.
        """
        start_time = time.time()
        api_logger = await get_api_query_logger()
        error_message = None
        response_text = ""
        
        try:
            param = request.to_query_params(False)
            response = await rag.aquery(request.query, param=param)

            # If response is a string (e.g. cache hit), return directly
            if isinstance(response, str):
                response_text = response
                return QueryResponse(response=response)

            if isinstance(response, dict):
                result = json.dumps(response, indent=2)
                response_text = result
                return QueryResponse(response=result)
            else:
                response_text = str(response)
                return QueryResponse(response=str(response))
                
        except Exception as e:
            error_message = str(e)
            response_text = f"Error: {error_message}"
            trace_exception(e)
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            # Log the API query and response
            end_time = time.time()
            response_time_ms = (end_time - start_time) * 1000
            
            await api_logger.log_api_query(
                query_text=request.query,
                response_text=response_text,
                endpoint="/query",
                query_mode=request.mode,
                response_time_ms=response_time_ms,
                error_message=error_message,
                request_params=request.model_dump(),
                is_streaming=False,
            )

    @router.post("/query/stream", dependencies=[Depends(combined_auth)])
    async def query_text_stream(request: QueryRequest):
        """
        This endpoint performs a retrieval-augmented generation (RAG) query and streams the response.

        Args:
            request (QueryRequest): The request object containing the query parameters.
            optional_api_key (Optional[str], optional): An optional API key for authentication. Defaults to None.

        Returns:
            StreamingResponse: A streaming response containing the RAG query results.
        """
        start_time = time.time()
        api_logger = await get_api_query_logger()
        error_message = None
        streamed_content = []
        
        try:
            param = request.to_query_params(True)
            result = await rag.aquery(request.query, param=param)
            
            # Handle AdvancedLightRAG tuple return format
            if isinstance(result, tuple):
                response, retrieval_details = result
            else:
                response = result

            from fastapi.responses import StreamingResponse

            async def stream_generator():
                nonlocal error_message, streamed_content
                
                if isinstance(response, str):
                    # If it's a string, send it all at once
                    streamed_content.append(response)
                    yield f"{json.dumps({'response': response})}\n"
                else:
                    # If it's an async generator, send chunks one by one
                    try:
                        async for chunk in response:
                            if chunk:  # Only send non-empty content
                                streamed_content.append(chunk)
                                yield f"{json.dumps({'response': chunk})}\n"
                    except Exception as e:
                        error_message = str(e)
                        logging.error(f"Streaming error: {error_message}")
                        yield f"{json.dumps({'error': error_message})}\n"

            # Create the streaming response
            streaming_response = StreamingResponse(
                stream_generator(),
                media_type="application/x-ndjson",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "Content-Type": "application/x-ndjson",
                    "X-Accel-Buffering": "no",  # Ensure proper handling of streaming response when proxied by Nginx
                },
            )
            
            # Log the streaming query (response will be "[Streaming Response]" since we can't capture streamed content easily)
            end_time = time.time()
            response_time_ms = (end_time - start_time) * 1000
            
            # For streaming responses, we log immediately but with a placeholder response text
            await api_logger.log_api_query(
                query_text=request.query,
                response_text="[Streaming Response]",
                endpoint="/query/stream",
                query_mode=request.mode,
                response_time_ms=response_time_ms,
                error_message=error_message,
                request_params=request.model_dump(),
                is_streaming=True,
            )
            
            return streaming_response
            
        except Exception as e:
            error_message = str(e)
            end_time = time.time()
            response_time_ms = (end_time - start_time) * 1000
            
            # Log the error
            await api_logger.log_api_query(
                query_text=request.query,
                response_text=f"Error: {error_message}",
                endpoint="/query/stream",
                query_mode=request.mode,
                response_time_ms=response_time_ms,
                error_message=error_message,
                request_params=request.model_dump(),
                is_streaming=True,
            )
            
            trace_exception(e)
            raise HTTPException(status_code=500, detail=str(e))

    return router
