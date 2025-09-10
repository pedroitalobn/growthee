import time
import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from functools import wraps
import asyncio
import aiofiles
import os
from ..models import APIRequestLog

class APITracker:
    def __init__(self):
        self.logs_file = "api_requests.jsonl"
        self.service_costs = {
            "brave_browser": 0.001,  # $0.001 per request
            "firecrawl": 0.002,     # $0.002 per request
            "deepseek": 0.00014,    # $0.00014 per 1K tokens
            "chatgpt": 0.002,       # $0.002 per 1K tokens
            "claude": 0.003,        # $0.003 per 1K tokens
            "openai": 0.002,        # $0.002 per 1K tokens
            "anthropic": 0.003,     # $0.003 per 1K tokens
            "google_ai": 0.0015,    # $0.0015 per 1K tokens
            "perplexity": 0.002,    # $0.002 per 1K tokens
            "together_ai": 0.0008,  # $0.0008 per 1K tokens
        }
    
    def calculate_cost(self, service_name: str, tokens: Optional[int] = None) -> float:
        """Calculate cost based on service and tokens used"""
        base_cost = self.service_costs.get(service_name.lower(), 0.001)
        
        if tokens and service_name.lower() in ["deepseek", "chatgpt", "claude", "openai", "anthropic", "google_ai", "perplexity", "together_ai"]:
            return (tokens / 1000) * base_cost
        
        return base_cost
    
    async def log_request(self, log_data: APIRequestLog):
        """Log API request to file"""
        try:
            log_entry = log_data.dict()
            log_entry["id"] = str(uuid.uuid4())
            log_entry["timestamp"] = datetime.utcnow().isoformat()
            
            # Calculate cost if not provided
            if log_entry["cost_usd"] is None:
                log_entry["cost_usd"] = self.calculate_cost(
                    log_entry["service_name"], 
                    log_entry.get("tokens_used")
                )
            
            async with aiofiles.open(self.logs_file, "a") as f:
                await f.write(json.dumps(log_entry) + "\n")
        except Exception as e:
            print(f"Error logging API request: {e}")
    
    def track_api_call(self, service_name: str, endpoint: str = ""):
        """Decorator to track API calls"""
        def decorator(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                start_time = time.time()
                log_data = APIRequestLog(
                    service_name=service_name,
                    endpoint=endpoint or func.__name__,
                    method="POST",
                    request_data=kwargs if kwargs else None,
                    user_id=kwargs.get("user_id"),
                    timestamp=datetime.utcnow().isoformat()
                )
                
                try:
                    result = await func(*args, **kwargs)
                    response_time = (time.time() - start_time) * 1000
                    
                    log_data.response_status = 200
                    log_data.response_time_ms = response_time
                    
                    # Extract tokens from result if available
                    if isinstance(result, dict):
                        log_data.tokens_used = result.get("tokens_used") or result.get("usage", {}).get("total_tokens")
                    
                    await self.log_request(log_data)
                    return result
                    
                except Exception as e:
                    response_time = (time.time() - start_time) * 1000
                    log_data.response_status = 500
                    log_data.response_time_ms = response_time
                    log_data.error_message = str(e)
                    
                    await self.log_request(log_data)
                    raise
            
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                start_time = time.time()
                log_data = APIRequestLog(
                    service_name=service_name,
                    endpoint=endpoint or func.__name__,
                    method="POST",
                    request_data=kwargs if kwargs else None,
                    user_id=kwargs.get("user_id"),
                    timestamp=datetime.utcnow().isoformat()
                )
                
                try:
                    result = func(*args, **kwargs)
                    response_time = (time.time() - start_time) * 1000
                    
                    log_data.response_status = 200
                    log_data.response_time_ms = response_time
                    
                    # Extract tokens from result if available
                    if isinstance(result, dict):
                        log_data.tokens_used = result.get("tokens_used") or result.get("usage", {}).get("total_tokens")
                    
                    # Run async log in background
                    asyncio.create_task(self.log_request(log_data))
                    return result
                    
                except Exception as e:
                    response_time = (time.time() - start_time) * 1000
                    log_data.response_status = 500
                    log_data.response_time_ms = response_time
                    log_data.error_message = str(e)
                    
                    # Run async log in background
                    asyncio.create_task(self.log_request(log_data))
                    raise
            
            return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
        return decorator

# Global tracker instance
api_tracker = APITracker()

# Convenience decorators for common services
def track_brave_browser(endpoint: str = ""):
    return api_tracker.track_api_call("brave_browser", endpoint)

def track_firecrawl(endpoint: str = ""):
    return api_tracker.track_api_call("firecrawl", endpoint)

def track_deepseek(endpoint: str = ""):
    return api_tracker.track_api_call("deepseek", endpoint)

def track_chatgpt(endpoint: str = ""):
    return api_tracker.track_api_call("chatgpt", endpoint)

def track_claude(endpoint: str = ""):
    return api_tracker.track_api_call("claude", endpoint)

def track_openai(endpoint: str = ""):
    return api_tracker.track_api_call("openai", endpoint)

def track_anthropic(endpoint: str = ""):
    return api_tracker.track_api_call("anthropic", endpoint)

def track_google_ai(endpoint: str = ""):
    return api_tracker.track_api_call("google_ai", endpoint)

def track_perplexity(endpoint: str = ""):
    return api_tracker.track_api_call("perplexity", endpoint)

def track_together_ai(endpoint: str = ""):
    return api_tracker.track_api_call("together_ai", endpoint)