from datetime import datetime
import json
import os
from typing import Dict, Any
import asyncio
import inspect

class LogService:
    def __init__(self):
        self.log_dir = 'logs'
        self.access_log = 'linkedin_access.log'
        self.performance_log = 'linkedin_performance.log'
        self.debug_log = 'linkedin_debug.log'
        self._ensure_log_directory()

    def _ensure_log_directory(self):
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
    
    def _make_serializable(self, obj: Any) -> Any:
        """Converte objetos não serializáveis em strings ou valores serializáveis"""
        if obj is None:
            return None
        elif isinstance(obj, (str, int, float, bool)):
            return obj
        elif isinstance(obj, (list, tuple)):
            return [self._make_serializable(item) for item in obj]
        elif isinstance(obj, dict):
            return {key: self._make_serializable(value) for key, value in obj.items()}
        elif asyncio.iscoroutine(obj):
            return f"<coroutine: {obj.__name__ if hasattr(obj, '__name__') else str(obj)}>"
        elif inspect.isfunction(obj) or inspect.ismethod(obj):
            return f"<function: {obj.__name__}>"
        elif hasattr(obj, '__dict__'):
            return f"<object: {obj.__class__.__name__}>"
        else:
            return str(obj)

    def log_access(self, action: str, details: Dict[str, Any]):
        timestamp = datetime.now().isoformat()
        log_entry = {
            'timestamp': timestamp,
            'action': action,
            'details': self._make_serializable(details)
        }
        
        with open(os.path.join(self.log_dir, self.access_log), 'a') as f:
            f.write(json.dumps(log_entry) + '\n')

    def log_performance(self, operation: str, start_time: float, end_time: float, details: Dict[str, Any]):
        duration = end_time - start_time
        timestamp = datetime.now().isoformat()
        
        log_entry = {
            'timestamp': timestamp,
            'operation': operation,
            'duration_seconds': duration,
            'details': self._make_serializable(details)
        }
        
        with open(os.path.join(self.log_dir, self.performance_log), 'a') as f:
            f.write(json.dumps(log_entry) + '\n')

    def log_debug(self, message: str, details: Dict[str, Any] = None):
        timestamp = datetime.now().isoformat()
        log_entry = {
            'timestamp': timestamp,
            'message': message,
            'details': self._make_serializable(details or {})
        }
        
        with open(os.path.join(self.log_dir, self.debug_log), 'a') as f:
            f.write(json.dumps(log_entry) + '\n')