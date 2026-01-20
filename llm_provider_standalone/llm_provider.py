#!/usr/bin/env python3
"""
LLMProvider - Universal LLM abstraction layer with comprehensive logging

Features:
- Multi-provider support via LiteLLM (auto-detects responses() vs completion() API)
- Structured output support via Pydantic models
- Jinja2 template rendering with robust special character handling
- Comprehensive timestamped logging of all LLM calls
- Response caching for cost savings and speed
- Async-first with sync convenience methods
- Batch parallel processing with rate limiting
- Automatic retry logic with exponential backoff
- Cost and usage tracking
"""

import os
import json
import asyncio
import hashlib
import warnings
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable, Type, Union, AsyncIterator
from dataclasses import dataclass, asdict

import litellm
from pydantic import BaseModel
from jinja2 import Environment, Template
from dotenv import load_dotenv

# Suppress LiteLLM's verbose "Give Feedback" messages
litellm.suppress_debug_info = True

# Load environment variables
load_dotenv()


@dataclass
class LLMCallMetadata:
    """Metadata for a single LLM call"""
    timestamp: str
    request_id: str
    model: str
    parameters: Dict[str, Any]
    prompt: Dict[str, Any]
    response: Dict[str, Any]
    timing: Dict[str, Any]
    metadata: Dict[str, Any]


class LLMError(Exception):
    """Base exception for LLM errors"""
    pass


class RetryableError(LLMError):
    """Errors that should trigger retry (network, rate limit, etc.)"""
    pass


class PermanentError(LLMError):
    """Errors that should not be retried (auth, invalid params, etc.)"""
    pass


class LLMProvider:
    """
    Universal LLM provider with comprehensive logging and robust error handling.

    Example:
        provider = LLMProvider(
            model="gpt-5-mini-2025-08-07",
            log_dir="llm_logs",
            progress_callback=lambda p: print(f"Progress: {p['message']}")
        )

        # Simple text generation
        result = await provider.generate_async("What is 2+2?")

        # Structured output
        class Person(BaseModel):
            name: str
            age: int

        person = await provider.generate_async(
            "Generate a person named John, age 30",
            response_model=Person
        )

        # Batch processing
        results = await provider.generate_batch([
            "Question 1", "Question 2", "Question 3"
        ])
    """

    def __init__(
        self,
        model: str = "gpt-5-mini-2025-08-07",
        log_dir: str = "llm_logs",
        timeout: float = 300.0,
        max_retries: int = 3,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        api_key: Optional[str] = None,
        log_retention_days: Optional[int] = None,
        cache_dir: Optional[str] = None,
        cache_ttl: Optional[int] = None,
        extra_metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize LLMProvider.

        Args:
            model: Model identifier (default: gpt-5-mini-2025-08-07)
            log_dir: Directory for timestamped log files
            timeout: Request timeout in seconds (default: 300s, no artificial limits)
            max_retries: Number of retry attempts for retryable errors
            progress_callback: Optional callback for progress updates
            api_key: Optional API key (uses OPENAI_API_KEY env var if not provided)
            log_retention_days: Automatically delete logs older than N days (None = keep forever)
            cache_dir: Directory for response cache (None = no caching)
            cache_ttl: Cache time-to-live in seconds (None = cache forever)
            extra_metadata: Additional metadata to include in every log entry (e.g., agent_id, run_id)
        """
        self.model = model
        self.log_dir = Path(log_dir)
        self.timeout = timeout
        self.max_retries = max_retries
        self.progress_callback = progress_callback
        self.log_retention_days = log_retention_days
        self.cache_dir = Path(cache_dir) if cache_dir else None
        self.cache_ttl = cache_ttl
        self.extra_metadata: Dict[str, Any] = extra_metadata or {}

        # Create log directory
        self.log_dir.mkdir(exist_ok=True)

        # Create cache directory if caching enabled
        if self.cache_dir:
            self.cache_dir.mkdir(exist_ok=True, parents=True)

        # Clean old logs if retention policy is set
        if self.log_retention_days is not None:
            self._cleanup_old_logs()

        # Setup API key
        if api_key:
            os.environ["OPENAI_API_KEY"] = api_key

        # Jinja2 environment for template rendering
        self.jinja_env = Environment(
            autoescape=False,  # We want literal strings for LLM prompts
            trim_blocks=True,
            lstrip_blocks=True
        )

        # Usage tracking
        self.usage_stats = {
            "total_tokens": 0,
            "requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_cost": 0.0,
            "total_duration": 0.0,
            "cache_hits": 0,
            "cache_misses": 0,
        }

        # Retry tracking (for accurate retry count)
        self._current_retry_count = 0

        # Per-call usage tracking (for billing/costing)
        self.last_usage = {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "cost": 0.0
        }

    def _cleanup_old_logs(self) -> None:
        """Delete log directories older than log_retention_days"""
        from datetime import timedelta

        if self.log_retention_days is None:
            return

        cutoff_date = datetime.now() - timedelta(days=self.log_retention_days)

        # Iterate through date subdirectories
        for date_dir in self.log_dir.iterdir():
            if not date_dir.is_dir():
                continue

            # Parse directory name as date (YYYYMMDD format)
            try:
                dir_date = datetime.strptime(date_dir.name, "%Y%m%d")
                if dir_date < cutoff_date:
                    # Delete old directory
                    import shutil
                    shutil.rmtree(date_dir)
                    import logging
                    logging.info(f"Deleted old log directory: {date_dir}")
            except ValueError:
                # Not a valid date directory, skip
                continue

    def _generate_cache_key(
        self,
        prompt: str,
        model: str,
        response_model: Optional[Type[BaseModel]] = None,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None
    ) -> str:
        """Generate cache key from prompt and parameters"""
        key_data = {
            "model": model,
            "prompt": prompt,
            "system_prompt": system_prompt,
            "temperature": temperature,
            "response_model": response_model.__name__ if response_model else None,
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_str.encode()).hexdigest()

    def _get_cached_response(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached response if available and not expired"""
        if not self.cache_dir:
            return None

        cache_file = self.cache_dir / f"{cache_key}.json"

        if not cache_file.exists():
            return None

        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cached = json.load(f)

            # Check TTL if set
            if self.cache_ttl is not None:
                cached_time = datetime.fromisoformat(cached['cached_at'])
                age_seconds = (datetime.now() - cached_time).total_seconds()

                if age_seconds > self.cache_ttl:
                    # Cache expired, delete it
                    cache_file.unlink()
                    return None

            return cached

        except Exception:
            # If cache read fails, just treat as cache miss
            return None

    def _save_to_cache(
        self,
        cache_key: str,
        response_content: str,
        response_model: Optional[Type[BaseModel]] = None,
        parsed_result: Optional[BaseModel] = None
    ) -> None:
        """Save response to cache"""
        if not self.cache_dir:
            return

        cache_file = self.cache_dir / f"{cache_key}.json"

        try:
            cache_data = {
                "cached_at": datetime.now().isoformat(),
                "content": response_content,
                "response_type": "structured" if response_model else "text",
                "response_model": response_model.__name__ if response_model else None,
                "parsed_model": parsed_result.model_dump() if parsed_result else None,
            }

            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)

        except Exception:
            # If cache write fails, just continue without caching
            pass

    def clear_cache(self) -> int:
        """Clear all cached responses. Returns number of entries cleared."""
        if not self.cache_dir or not self.cache_dir.exists():
            return 0

        count = 0
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                cache_file.unlink()
                count += 1
            except Exception:
                pass

        return count

    def _is_responses_api_model(self, model: str) -> bool:
        """Check if model needs responses() API instead of completion()"""
        return 'gpt-5' in model.lower()

    def _generate_request_id(self) -> str:
        """Generate unique request ID (12 chars, collision-resistant)"""
        import uuid
        return uuid.uuid4().hex[:12]

    def _normalize_prompt(
        self,
        prompt: Union[str, Template],
        **context
    ) -> tuple[str, str]:
        """
        Normalize prompt to handle special characters robustly.

        Returns:
            (raw_prompt, rendered_prompt): Both original and rendered versions
        """
        if isinstance(prompt, Template):
            raw = prompt.source if hasattr(prompt, 'source') else str(prompt)
            rendered = prompt.render(**context)
        elif isinstance(prompt, str):
            raw = prompt
            if context:
                # Treat string as Jinja2 template if context provided
                template = self.jinja_env.from_string(prompt)
                rendered = template.render(**context)
            else:
                rendered = prompt
        else:
            raise TypeError(f"Prompt must be str or Template, got {type(prompt)}")

        return raw, rendered

    def _prepare_structured_output(
        self,
        model: str,
        response_model: Type[BaseModel]
    ) -> Dict[str, Any]:
        """
        Prepare structured output parameters based on model type.

        Args:
            model: Model identifier
            response_model: Pydantic model class for structured output

        Returns:
            Dict with appropriate format parameters for the model
        """
        schema = response_model.model_json_schema()

        # Ensure additionalProperties is set to false for strict mode
        if 'additionalProperties' not in schema:
            schema['additionalProperties'] = False

        # GPT-5-mini strict mode requires ALL properties to be in 'required' array
        if 'properties' in schema and 'required' not in schema:
            schema['required'] = list(schema['properties'].keys())
        elif 'properties' in schema and 'required' in schema:
            # Ensure all properties are in required (even optional ones with defaults)
            all_props = set(schema['properties'].keys())
            current_required = set(schema.get('required', []))
            missing = all_props - current_required
            if missing:
                schema['required'] = list(all_props)

        # Recursively ensure nested objects also have additionalProperties: false and required fields
        def ensure_strict_schema(obj):
            if isinstance(obj, dict):
                # Handle object types
                if obj.get('type') == 'object':
                    if 'additionalProperties' not in obj:
                        obj['additionalProperties'] = False
                    # Gemini requires OBJECT types to have non-empty properties
                    # If no properties defined (e.g., dict[str, Any]), convert to string
                    # to accept JSON strings instead
                    if 'properties' not in obj or not obj['properties']:
                        obj['type'] = 'string'
                        obj.pop('additionalProperties', None)
                        obj.pop('properties', None)
                        obj.pop('required', None)
                    else:
                        # Ensure all properties are required
                        if 'required' not in obj:
                            obj['required'] = list(obj['properties'].keys())
                        else:
                            all_props = set(obj['properties'].keys())
                            current_required = set(obj.get('required', []))
                            missing = all_props - current_required
                            if missing:
                                obj['required'] = list(all_props)
                # Recurse into nested structures
                for value in obj.values():
                    ensure_strict_schema(value)
            elif isinstance(obj, list):
                for item in obj:
                    ensure_strict_schema(item)

        ensure_strict_schema(schema)

        if self._is_responses_api_model(model):
            # GPT-5-mini uses text parameter with json_schema format
            return {
                "text": {
                    "format": {
                        "type": "json_schema",
                        "name": response_model.__name__,
                        "schema": schema,
                        "strict": True
                    }
                }
            }
        else:
            # Other models use response_format parameter
            return {
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {
                        "name": response_model.__name__,
                        "schema": schema,
                        "strict": True
                    }
                }
            }

    def _convert_messages_to_input(self, messages: List[Dict[str, str]]) -> str:
        """Convert messages array to input string for responses() API"""
        parts = []
        for msg in messages:
            role = msg.get('role', 'user')
            content = msg.get('content', '')

            if role == 'system':
                parts.append(f"System: {content}")
            elif role == 'assistant':
                parts.append(f"Assistant: {content}")
            else:  # user
                if len(parts) > 0 and parts[0].startswith("System:"):
                    parts.append(content)
                else:
                    parts.append(f"User: {content}")

        return "\n\n".join(parts)

    def _extract_responses_content(self, response) -> str:
        """Extract text from responses() API response"""
        # Handle incomplete responses
        if hasattr(response, 'status') and response.status == 'incomplete':
            if hasattr(response, 'output') and response.output:
                texts = []
                for item in response.output:
                    if hasattr(item, 'content'):
                        for content in item.content:
                            if hasattr(content, 'text'):
                                texts.append(content.text)
                if texts:
                    return "\n".join(texts)
            return f"Response incomplete (status: {response.status})"

        # Handle completed responses with message type
        if hasattr(response, 'output') and response.output:
            for item in response.output:
                if hasattr(item, 'type') and item.type == 'message':
                    if hasattr(item, 'content'):
                        texts = []
                        for content in item.content:
                            if hasattr(content, 'text'):
                                texts.append(content.text)
                        if texts:
                            return "\n".join(texts)

        # Fallback
        if hasattr(response, 'output_text'):
            return response.output_text

        return str(response)

    def _extract_usage_stats(self, response) -> Dict[str, Any]:
        """Extract usage stats from response, handling different API structures"""
        if not hasattr(response, 'usage'):
            return None

        usage = response.usage

        # Debug logging to investigate token breakdown
        import logging
        logging.debug(f"Usage object type: {type(usage)}")
        logging.debug(f"Usage attributes: {[attr for attr in dir(usage) if not attr.startswith('_')]}")
        if hasattr(usage, '__dict__'):
            logging.debug(f"Usage __dict__: {usage.__dict__}")

        # Try responses API structure first (has both input/output AND total)
        if hasattr(usage, 'input_tokens') and hasattr(usage, 'output_tokens'):
            result = {
                "total_tokens": usage.total_tokens if hasattr(usage, 'total_tokens') else (usage.input_tokens + usage.output_tokens),
                "prompt_tokens": usage.input_tokens,
                "completion_tokens": usage.output_tokens,
            }
            # Check for details if available
            if hasattr(usage, 'output_tokens_details'):
                details = usage.output_tokens_details
                if hasattr(details, 'reasoning_tokens') and details.reasoning_tokens:
                    result['reasoning_tokens'] = details.reasoning_tokens
            return result
        # Try completion API structure
        elif hasattr(usage, 'total_tokens'):
            return {
                "total_tokens": usage.total_tokens,
                "prompt_tokens": getattr(usage, 'prompt_tokens', None),
                "completion_tokens": getattr(usage, 'completion_tokens', None),
            }
        # Check for alternate attribute names
        elif hasattr(usage, 'prompt_cache_hit_tokens') or hasattr(usage, 'prompt_cache_miss_tokens'):
            # Some APIs expose cache-related tokens
            prompt_tokens = (getattr(usage, 'prompt_cache_hit_tokens', 0) +
                           getattr(usage, 'prompt_cache_miss_tokens', 0))
            completion_tokens = getattr(usage, 'completion_tokens', None)
            total = prompt_tokens + (completion_tokens or 0) if completion_tokens else None
            return {
                "total_tokens": total,
                "prompt_tokens": prompt_tokens if prompt_tokens > 0 else None,
                "completion_tokens": completion_tokens,
                "cache_hit": getattr(usage, 'prompt_cache_hit_tokens', None),
                "cache_miss": getattr(usage, 'prompt_cache_miss_tokens', None),
            }
        # Fallback - log all attributes for investigation
        else:
            all_attrs = {attr: getattr(usage, attr, None)
                        for attr in dir(usage)
                        if not attr.startswith('_') and not callable(getattr(usage, attr))}
            logging.warning(f"Unknown usage structure. All attributes: {all_attrs}")
            return {
                "total_tokens": getattr(usage, 'total_tokens', None),
                "prompt_tokens": None,
                "completion_tokens": None,
                "raw_usage": str(usage),
                "debug_all_attributes": all_attrs,
            }

    def _log_call(self, call_metadata: LLMCallMetadata) -> None:
        """Write comprehensive log of LLM call to timestamped JSON file"""
        now = datetime.now()

        # Create date-based subdirectory (e.g., llm_logs/20251101/)
        date_dir = self.log_dir / now.strftime("%Y%m%d")
        date_dir.mkdir(exist_ok=True)

        # Include microseconds to avoid collisions
        timestamp_str = now.strftime("%Y%m%d_%H%M%S_%f")[:20]  # YYYYMMDD_HHMMSS_mmmmmm -> 20 chars
        log_file = date_dir / f"{timestamp_str}_{call_metadata.request_id}.json"

        # Merge extra_metadata into the log entry
        log_data = asdict(call_metadata)
        if self.extra_metadata:
            log_data["metadata"] = {**log_data.get("metadata", {}), **self.extra_metadata}

        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)

    async def _call_llm_with_retry(
        self,
        model: str,
        messages: Optional[List[Dict[str, str]]] = None,
        input_text: Optional[str] = None,
        **kwargs
    ):
        """
        Internal method to call LLM with manual retry logic.

        Raises RetryableError for transient failures, PermanentError for permanent ones.
        """
        # Reset retry count for this call
        self._current_retry_count = 0
        last_exception = None

        for attempt in range(self.max_retries + 1):  # +1 because first attempt is not a retry
            try:
                if self._is_responses_api_model(model):
                    # Use responses() API for gpt-5 models
                    if not input_text:
                        input_text = self._convert_messages_to_input(messages)

                    # Remove completion-only params
                    kwargs.pop('response_format', None)
                    kwargs.pop('max_tokens', None)

                    response = await litellm.aresponses(
                        model=model,
                        input=input_text,
                        **kwargs
                    )
                    return response
                else:
                    # Use completion() API for other models
                    response = await litellm.acompletion(
                        model=model,
                        messages=messages,
                        timeout=self.timeout,
                        **kwargs
                    )
                    return response

            except Exception as e:
                last_exception = e
                error_str = str(e).lower()

                # Classify error types
                if any(x in error_str for x in ['rate limit', 'timeout', 'connection', 'network', '429', '503', '504']):
                    # Retryable error
                    if attempt < self.max_retries:
                        self._current_retry_count = attempt + 1
                        # Exponential backoff: min(1 * 2^attempt, 10) seconds
                        wait_time = min(1 * (2 ** attempt), 10)
                        import logging
                        logging.info(f"Retry {self._current_retry_count}/{self.max_retries} after {wait_time}s: {e}")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        # Out of retries
                        raise RetryableError(f"Retryable error after {self.max_retries} retries: {e}") from e
                elif any(x in error_str for x in ['auth', 'invalid', 'api key', '401', '403']):
                    # Permanent error - don't retry
                    raise PermanentError(f"Permanent error: {e}") from e
                else:
                    # Conservative: unknown errors are permanent to avoid retry loops on bugs
                    import logging
                    logging.warning(f"Unclassified error (treating as permanent): {error_str}")
                    raise PermanentError(f"Unclassified error: {e}") from e

        # Should never reach here, but just in case
        raise RetryableError(f"Failed after {self.max_retries} retries: {last_exception}") from last_exception

    async def generate_async(
        self,
        prompt: Union[str, Template],
        response_model: Optional[Type[BaseModel]] = None,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        use_cache: bool = True,
        **context
    ) -> Union[str, BaseModel]:
        """
        Generate LLM response asynchronously.

        Args:
            prompt: Prompt string or Jinja2 Template
            response_model: Optional Pydantic model for structured output
            system_prompt: Optional system prompt
            temperature: Temperature (ignored for gpt-5-mini with warning)
            use_cache: Whether to use cache (default: True, only if cache_dir set)
            **context: Context variables for Jinja2 template rendering

        Returns:
            Generated text or Pydantic model instance if response_model provided

        Raises:
            LLMError: If generation fails after retries
        """
        request_id = self._generate_request_id()
        start_time = datetime.now()

        # Normalize prompt
        raw_prompt, rendered_prompt = self._normalize_prompt(prompt, **context)

        # Check cache if enabled
        cache_key = None
        if use_cache and self.cache_dir:
            cache_key = self._generate_cache_key(
                prompt=rendered_prompt,
                model=self.model,
                response_model=response_model,
                system_prompt=system_prompt,
                temperature=temperature
            )

            cached = self._get_cached_response(cache_key)
            if cached:
                # Cache hit!
                self.usage_stats['cache_hits'] += 1
                self.usage_stats['requests'] += 1
                self.usage_stats['successful_requests'] += 1

                # Return cached response
                if response_model and cached.get('parsed_model'):
                    return response_model(**cached['parsed_model'])
                else:
                    return cached['content']

        # Build messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": rendered_prompt})

        # Prepare parameters
        params = {}
        warnings_list = []

        # Handle temperature
        if temperature is not None and 'gpt-5-mini' in self.model:
            warnings.warn(
                "gpt-5-mini does not support temperature parameter (ignoring)",
                UserWarning,
                stacklevel=2
            )
            warnings_list.append("temperature ignored for gpt-5-mini")
        elif temperature is not None:
            params['temperature'] = temperature

        # Handle structured output
        if response_model:
            structured_params = self._prepare_structured_output(self.model, response_model)
            params.update(structured_params)

        # Execute call
        try:
            response = await self._call_llm_with_retry(
                model=self.model,
                messages=messages,
                **params
            )

            # Extract content
            if self._is_responses_api_model(self.model):
                content = self._extract_responses_content(response)
            else:
                content = (response.choices[0].message.content
                          if (hasattr(response, 'choices') and response.choices)
                          else str(response))

            # Parse structured output if requested
            parsed_result = None
            if response_model:
                parsed_result = response_model.model_validate_json(content)
                final_result = parsed_result
            else:
                final_result = content

            # Cache miss - save to cache if enabled
            if cache_key:
                self.usage_stats['cache_misses'] += 1
                self._save_to_cache(cache_key, content, response_model, parsed_result)

            # Update usage stats
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            self.usage_stats['requests'] += 1
            self.usage_stats['successful_requests'] += 1
            self.usage_stats['total_duration'] += duration

            # Extract and store per-call usage
            self.last_usage = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "cost": 0.0}
            if hasattr(response, 'usage'):
                usage = response.usage
                # Handle different usage object structures (responses API vs completion API)
                if hasattr(usage, 'input_tokens') and hasattr(usage, 'output_tokens'):
                    # responses() API structure
                    self.last_usage["input_tokens"] = usage.input_tokens
                    self.last_usage["output_tokens"] = usage.output_tokens
                    self.last_usage["total_tokens"] = usage.input_tokens + usage.output_tokens
                    self.usage_stats['total_tokens'] += self.last_usage["total_tokens"]
                elif hasattr(usage, 'prompt_tokens') and hasattr(usage, 'completion_tokens'):
                    # completion() API structure
                    self.last_usage["input_tokens"] = usage.prompt_tokens or 0
                    self.last_usage["output_tokens"] = usage.completion_tokens or 0
                    self.last_usage["total_tokens"] = usage.total_tokens or (self.last_usage["input_tokens"] + self.last_usage["output_tokens"])
                    self.usage_stats['total_tokens'] += self.last_usage["total_tokens"]
                elif hasattr(usage, 'total_tokens'):
                    self.last_usage["total_tokens"] = usage.total_tokens
                    self.usage_stats['total_tokens'] += usage.total_tokens

                try:
                    cost = litellm.completion_cost(completion_response=response)
                    self.last_usage["cost"] = cost
                    self.usage_stats['total_cost'] += cost
                except Exception as e:
                    import logging
                    logging.debug(f"Cost tracking unavailable: {e}")

            # Log call
            call_metadata = LLMCallMetadata(
                timestamp=start_time.isoformat(),
                request_id=request_id,
                model=self.model,
                parameters={
                    "temperature": temperature,
                    "max_tokens": None,
                    "warnings": warnings_list,
                    "response_model": response_model.__name__ if response_model else None,
                },
                prompt={
                    "raw": raw_prompt,
                    "rendered": rendered_prompt,
                    "context": context,
                    "system_prompt": system_prompt,
                    "length_chars": len(rendered_prompt),
                    "hash": hashlib.sha256(rendered_prompt.encode()).hexdigest()[:16],
                },
                response={
                    "content": content,
                    "length_chars": len(content),
                    "type": "structured" if response_model else "text",
                    "parsed_model": parsed_result.model_dump() if parsed_result else None,
                },
                timing={
                    "start": start_time.isoformat(),
                    "end": end_time.isoformat(),
                    "duration_seconds": duration,
                },
                metadata={
                    "api_method": "responses" if self._is_responses_api_model(self.model) else "completion",
                    "success": True,
                    "error": None,
                    "retry_count": self._current_retry_count,
                    "usage": self._extract_usage_stats(response) if hasattr(response, 'usage') else None,
                }
            )

            self._log_call(call_metadata)

            return final_result

        except Exception as e:
            # Log failed call
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            self.usage_stats['requests'] += 1
            self.usage_stats['failed_requests'] += 1

            call_metadata = LLMCallMetadata(
                timestamp=start_time.isoformat(),
                request_id=request_id,
                model=self.model,
                parameters={
                    "temperature": temperature,
                    "max_tokens": None,
                    "warnings": warnings_list,
                    "response_model": response_model.__name__ if response_model else None,
                },
                prompt={
                    "raw": raw_prompt,
                    "rendered": rendered_prompt,
                    "context": context,
                    "system_prompt": system_prompt,
                    "length_chars": len(rendered_prompt),
                    "hash": hashlib.sha256(rendered_prompt.encode()).hexdigest()[:16],
                },
                response={
                    "content": None,
                    "length_chars": 0,
                    "type": None,
                    "parsed_model": None,
                },
                timing={
                    "start": start_time.isoformat(),
                    "end": end_time.isoformat(),
                    "duration_seconds": duration,
                },
                metadata={
                    "api_method": "responses" if self._is_responses_api_model(self.model) else "completion",
                    "success": False,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "retry_count": self._current_retry_count,
                    "usage": None,
                }
            )

            self._log_call(call_metadata)
            raise LLMError(f"LLM generation failed after {self.max_retries} retries: {e}") from e

    def generate(
        self,
        prompt: Union[str, Template],
        response_model: Optional[Type[BaseModel]] = None,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        **context
    ) -> Union[str, BaseModel]:
        """
        Synchronous wrapper for generate_async.

        See generate_async for documentation.
        """
        try:
            # Try to get running event loop
            loop = asyncio.get_running_loop()
            # If we're already in an event loop, we can't use asyncio.run()
            raise RuntimeError(
                "generate() cannot be called from an async context. "
                "Use await generate_async() instead."
            )
        except RuntimeError as e:
            if "no running event loop" in str(e).lower():
                # No event loop running, safe to use asyncio.run()
                return asyncio.run(self.generate_async(
                    prompt=prompt,
                    response_model=response_model,
                    system_prompt=system_prompt,
                    temperature=temperature,
                    **context
                ))
            else:
                # Already in event loop
                raise

    async def generate_stream(
        self,
        prompt: Union[str, Template],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        **context
    ) -> AsyncIterator[str]:
        """
        Generate LLM response with streaming for real-time feedback.

        Args:
            prompt: Prompt string or Jinja2 Template
            system_prompt: Optional system prompt
            temperature: Temperature (ignored for gpt-5-mini with warning)
            **context: Context variables for Jinja2 template rendering

        Yields:
            str: Chunks of generated text as they arrive

        Note:
            Structured output (response_model) is not supported in streaming mode.
            Streaming is particularly useful for long-running operations (6+ minutes).
        """
        request_id = self._generate_request_id()
        start_time = datetime.now()

        # Normalize prompt
        raw_prompt, rendered_prompt = self._normalize_prompt(prompt, **context)

        # Build messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": rendered_prompt})

        # Prepare parameters
        params = {}
        warnings_list = []

        # Handle temperature
        if temperature is not None and 'gpt-5-mini' in self.model:
            warnings.warn(
                "gpt-5-mini does not support temperature parameter (ignoring)",
                UserWarning,
                stacklevel=2
            )
            warnings_list.append("temperature ignored for gpt-5-mini")
        elif temperature is not None:
            params['temperature'] = temperature

        # Streaming only works with completion API currently
        if self._is_responses_api_model(self.model):
            # responses() API doesn't support streaming yet in litellm
            warnings.warn(
                f"Streaming not supported for {self.model}, falling back to non-streaming",
                UserWarning
            )
            result = await self.generate_async(prompt, system_prompt=system_prompt, temperature=temperature, **context)
            yield result
            return

        # Execute streaming call
        full_content = []
        try:
            response = await litellm.acompletion(
                model=self.model,
                messages=messages,
                stream=True,
                timeout=self.timeout,
                **params
            )

            async for chunk in response:
                if hasattr(chunk, 'choices') and chunk.choices:
                    delta = chunk.choices[0].delta
                    if hasattr(delta, 'content') and delta.content:
                        content_chunk = delta.content
                        full_content.append(content_chunk)
                        yield content_chunk

            # Log after streaming completes
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            full_text = ''.join(full_content)

            self.usage_stats['requests'] += 1
            self.usage_stats['successful_requests'] += 1
            self.usage_stats['total_duration'] += duration

            # Note: Usage stats not available in streaming mode
            call_metadata = LLMCallMetadata(
                timestamp=start_time.isoformat(),
                request_id=request_id,
                model=self.model,
                parameters={
                    "temperature": temperature,
                    "max_tokens": None,
                    "warnings": warnings_list,
                    "response_model": None,
                    "streaming": True,
                },
                prompt={
                    "raw": raw_prompt,
                    "rendered": rendered_prompt,
                    "context": context,
                    "system_prompt": system_prompt,
                    "length_chars": len(rendered_prompt),
                    "hash": hashlib.sha256(rendered_prompt.encode()).hexdigest()[:16],
                },
                response={
                    "content": full_text,
                    "length_chars": len(full_text),
                    "type": "text_stream",
                    "parsed_model": None,
                },
                timing={
                    "start": start_time.isoformat(),
                    "end": end_time.isoformat(),
                    "duration_seconds": duration,
                },
                metadata={
                    "api_method": "completion_stream",
                    "success": True,
                    "error": None,
                    "retry_count": 0,
                    "usage": None,  # Not available in streaming mode
                }
            )

            self._log_call(call_metadata)

        except Exception as e:
            # Log failed streaming call
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            self.usage_stats['requests'] += 1
            self.usage_stats['failed_requests'] += 1

            call_metadata = LLMCallMetadata(
                timestamp=start_time.isoformat(),
                request_id=request_id,
                model=self.model,
                parameters={
                    "temperature": temperature,
                    "max_tokens": None,
                    "warnings": warnings_list,
                    "response_model": None,
                    "streaming": True,
                },
                prompt={
                    "raw": raw_prompt,
                    "rendered": rendered_prompt,
                    "context": context,
                    "system_prompt": system_prompt,
                    "length_chars": len(rendered_prompt),
                    "hash": hashlib.sha256(rendered_prompt.encode()).hexdigest()[:16],
                },
                response={
                    "content": ''.join(full_content) if full_content else None,
                    "length_chars": len(''.join(full_content)) if full_content else 0,
                    "type": None,
                    "parsed_model": None,
                },
                timing={
                    "start": start_time.isoformat(),
                    "end": end_time.isoformat(),
                    "duration_seconds": duration,
                },
                metadata={
                    "api_method": "completion_stream",
                    "success": False,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "retry_count": 0,
                    "usage": None,
                }
            )

            self._log_call(call_metadata)
            raise LLMError(f"Streaming generation failed: {e}") from e

    async def generate_batch(
        self,
        prompts: List[Union[str, Template]],
        response_model: Optional[Type[BaseModel]] = None,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_concurrent: int = 5,
        **context
    ) -> List[Union[str, BaseModel]]:
        """
        Generate responses for multiple prompts in parallel.

        Args:
            prompts: List of prompts (strings or Templates)
            response_model: Optional Pydantic model for structured output
            system_prompt: Optional system prompt (applied to all)
            temperature: Temperature (ignored for gpt-5-mini)
            max_concurrent: Maximum concurrent requests (rate limiting)
            **context: Context variables for Jinja2 template rendering

        Returns:
            List of generated results (same order as input prompts)
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def bounded_generate(prompt: Union[str, Template], index: int):
            async with semaphore:
                if self.progress_callback:
                    self.progress_callback({
                        "current": index + 1,
                        "total": len(prompts),
                        "message": f"Processing {index + 1} of {len(prompts)}",
                    })

                return await self.generate_async(
                    prompt=prompt,
                    response_model=response_model,
                    system_prompt=system_prompt,
                    temperature=temperature,
                    **context
                )

        tasks = [bounded_generate(p, i) for i, p in enumerate(prompts)]
        # Use return_exceptions=True to handle partial failures
        # This way, one failure doesn't stop the entire batch
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert exceptions to None or re-raise if all failed
        failed_count = sum(1 for r in results if isinstance(r, Exception))
        if failed_count == len(results):
            # All tasks failed - raise the first exception
            raise LLMError(f"All {len(results)} batch tasks failed. First error: {results[0]}")

        return results

    def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics"""
        stats = self.usage_stats.copy()
        if stats['requests'] > 0:
            stats['avg_duration'] = stats['total_duration'] / stats['requests']
            stats['success_rate'] = stats['successful_requests'] / stats['requests']
        return stats

    def reset_usage_stats(self):
        """Reset usage statistics"""
        self.usage_stats = {
            "total_tokens": 0,
            "requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_cost": 0.0,
            "total_duration": 0.0,
            "cache_hits": 0,
            "cache_misses": 0,
        }


if __name__ == "__main__":
    # Example usage
    print("LLMProvider - see example_usage.py for comprehensive examples")
