import logging
from typing import List, Dict
from threading import Lock

logger = logging.getLogger("app.services.history_service")

class HistoryService:
    # Class-level storage for session memory
    _sessions: Dict[str, List[Dict[str, str]]] = {}
    _lock = Lock()
    
    # Maximum number of messages to keep in history per session
    MAX_HISTORY_LENGTH = 10

    @classmethod
    def get_history(cls, session_id: str) -> List[Dict[str, str]]:
        """
        Retrieve chat history for a session.
        """
        with cls._lock:
            if session_id not in cls._sessions:
                cls._sessions[session_id] = []
            return list(cls._sessions[session_id])

    @classmethod
    def add_message(cls, session_id: str, role: str, content: str):
        """
        Add a message to the session's chat history.
        Maintains sliding window of maximum length.
        """
        with cls._lock:
            if session_id not in cls._sessions:
                cls._sessions[session_id] = []
            
            cls._sessions[session_id].append({
                "role": role,
                "content": content
            })
            
            # If history exceeds limit, keep the most recent ones
            if len(cls._sessions[session_id]) > cls.MAX_HISTORY_LENGTH:
                cls._sessions[session_id] = cls._sessions[session_id][-cls.MAX_HISTORY_LENGTH:]
                logger.debug(f"Trimmed history for session {session_id} to last {cls.MAX_HISTORY_LENGTH} messages.")

    @classmethod
    def clear_history(cls, session_id: str):
        """
        Clear history for a given session.
        """
        with cls._lock:
            if session_id in cls._sessions:
                cls._sessions[session_id] = []
                logger.info(f"Cleared chat history for session: {session_id}")
