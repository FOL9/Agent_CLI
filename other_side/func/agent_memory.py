"""
SDX Agent Memory System
========================

Persistent memory to maintain context across conversations and sessions.

This module integrates with the existing memory system located at:
/home/user/agent/other_side/backend/memory

The memory system provides:
- Session insights and conversation history
- Codebase map (file purposes)
- Code patterns to follow
- Gotchas (pitfalls to avoid)
"""

import sys
import os
from pathlib import Path
from typing import Dict, List, Optional, Any

# Add the memory package to Python path
MEMORY_PATH = Path("/home/user/agent/other_side/backend/memory")
if str(MEMORY_PATH.parent) not in sys.path:
    sys.path.insert(0, str(MEMORY_PATH.parent))

# Import from the actual memory package
from memory import (
    save_session_insights,
    load_all_insights,
    update_codebase_map,
    load_codebase_map,
    append_pattern,
    load_patterns,
    append_gotcha,
    load_gotchas,
    get_memory_summary,
    get_memory_dir,
)

import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class AgentMemory:
    """
    Persistent memory for SDX Agent.
    
    Wraps the existing memory system to provide:
    - Conversation tracking
    - File purpose mapping
    - Pattern discovery
    - Gotcha recording
    """
    
    def __init__(self, working_dir: str):
        """
        Initialize memory system.
        
        Args:
            working_dir: Current working directory (used as spec_dir)
        """
        self.working_dir = Path(working_dir)
        
        # Create a .sdx_agent directory structure compatible with memory system
        self.spec_dir = self.working_dir / ".sdx_agent"
        self.spec_dir.mkdir(exist_ok=True)
        
        # Get memory directory from the imported memory system
        self.memory_dir = get_memory_dir(self.spec_dir)
        
        # Track conversation number
        self._conversation_counter = self._get_current_conversation_number()
    
    def _get_current_conversation_number(self) -> int:
        """Get the current conversation number from session insights"""
        insights = load_all_insights(self.spec_dir)
        return len(insights) + 1
    
    # ========================================================================
    # CONVERSATION MEMORY
    # ========================================================================
    
    def save_conversation(self, user_input: str, agent_response: str, 
                         function_calls: List[Dict] = None) -> int:
        """
        Save a conversation turn using the memory system.
        
        Args:
            user_input: User's message
            agent_response: Agent's response
            function_calls: List of function calls made
        
        Returns:
            Conversation number
        """
        # Build insights structure compatible with memory system
        insights = {
            "subtasks_completed": [],  # Could track tasks if needed
            "discoveries": {
                "files_understood": {},
                "patterns_found": [],
                "gotchas_encountered": []
            },
            "what_worked": [f"User query: {user_input[:100]}"],
            "what_failed": [],
            "recommendations_for_next_session": [],
            "conversation_data": {
                "user_input": user_input,
                "agent_response": agent_response,
                "function_calls": function_calls or [],
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }
        
        # Save using the memory system
        save_session_insights(self.spec_dir, self._conversation_counter, insights)
        
        conv_num = self._conversation_counter
        self._conversation_counter += 1
        
        return conv_num
    
    def get_recent_conversations(self, limit: int = 5) -> List[Dict]:
        """
        Get recent conversations from session insights.
        
        Args:
            limit: Number of recent conversations to retrieve
        
        Returns:
            List of conversation dictionaries
        """
        insights = load_all_insights(self.spec_dir)
        recent = insights[-limit:] if len(insights) > limit else insights
        
        conversations = []
        for insight in recent:
            conv_data = insight.get("conversation_data", {})
            if conv_data:
                conversations.append({
                    "conversation_number": insight.get("session_number"),
                    "timestamp": conv_data.get("timestamp", ""),
                    "user_input": conv_data.get("user_input", ""),
                    "agent_response": conv_data.get("agent_response", ""),
                    "function_calls": conv_data.get("function_calls", [])
                })
        
        return conversations
    
    def get_conversation_summary(self, limit: int = 10) -> str:
        """
        Get a summary of recent conversations.
        
        Args:
            limit: Number of recent conversations to summarize
        
        Returns:
            Formatted summary string
        """
        conversations = self.get_recent_conversations(limit)
        
        if not conversations:
            return ""
        
        summary = "## Recent Conversation History\n\n"
        for conv in conversations:
            conv_num = conv.get("conversation_number", "?")
            timestamp = conv.get("timestamp", "")
            user_msg = conv.get("user_input", "")[:100]
            
            summary += f"**Session {conv_num}** ({timestamp[:10]}):\n"
            summary += f"  User: {user_msg}...\n\n"
        
        return summary
    
    # ========================================================================
    # CODEBASE MAP
    # ========================================================================
    
    def update_codebase_map(self, discoveries: Dict[str, str]):
        """
        Update codebase map with file purposes.
        
        Args:
            discoveries: Dict mapping file paths to their purposes
        """
        update_codebase_map(self.spec_dir, discoveries)
    
    def get_codebase_map(self) -> Dict[str, str]:
        """
        Get the codebase map.
        
        Returns:
            Dict mapping file paths to purposes
        """
        return load_codebase_map(self.spec_dir)
    
    def get_codebase_summary(self) -> str:
        """
        Get formatted codebase map.
        
        Returns:
            Formatted string of file purposes
        """
        codebase_map = self.get_codebase_map()
        
        if not codebase_map:
            return ""
        
        summary = "## Known Codebase Files\n\n"
        for filepath, purpose in sorted(codebase_map.items()):
            summary += f"- **{filepath}**: {purpose}\n"
        
        return summary
    
    # ========================================================================
    # PATTERNS
    # ========================================================================
    
    def add_pattern(self, pattern: str):
        """
        Add a code pattern.
        
        Args:
            pattern: Description of the pattern
        """
        append_pattern(self.spec_dir, pattern)
    
    def get_patterns(self) -> List[str]:
        """
        Get all patterns.
        
        Returns:
            List of pattern strings
        """
        return load_patterns(self.spec_dir)
    
    def get_patterns_summary(self) -> str:
        """
        Get formatted patterns.
        
        Returns:
            Formatted string of patterns
        """
        patterns = self.get_patterns()
        
        if not patterns:
            return ""
        
        summary = "## Code Patterns to Follow\n\n"
        for pattern in patterns:
            summary += f"- {pattern}\n"
        
        return summary
    
    # ========================================================================
    # GOTCHAS
    # ========================================================================
    
    def add_gotcha(self, gotcha: str):
        """
        Add a gotcha/pitfall.
        
        Args:
            gotcha: Description of the pitfall
        """
        append_gotcha(self.spec_dir, gotcha)
    
    def get_gotchas(self) -> List[str]:
        """
        Get all gotchas.
        
        Returns:
            List of gotcha strings
        """
        return load_gotchas(self.spec_dir)
    
    def get_gotchas_summary(self) -> str:
        """
        Get formatted gotchas.
        
        Returns:
            Formatted string of gotchas
        """
        gotchas = self.get_gotchas()
        
        if not gotchas:
            return ""
        
        summary = "## Gotchas to Avoid\n\n"
        for gotcha in gotchas:
            summary += f"- {gotcha}\n"
        
        return summary
    
    # ========================================================================
    # FULL CONTEXT
    # ========================================================================
    
    def get_full_context(self) -> str:
        """
        Get complete memory context for system prompt injection.
        
        Returns:
            Formatted memory context string
        """
        context_parts = []
        
        # Recent conversations
        conv_summary = self.get_conversation_summary(limit=5)
        if conv_summary:
            context_parts.append(conv_summary)
        
        # Codebase map
        codebase_summary = self.get_codebase_summary()
        if codebase_summary:
            context_parts.append(codebase_summary)
        
        # Patterns
        patterns_summary = self.get_patterns_summary()
        if patterns_summary:
            context_parts.append(patterns_summary)
        
        # Gotchas
        gotchas_summary = self.get_gotchas_summary()
        if gotchas_summary:
            context_parts.append(gotchas_summary)
        
        if not context_parts:
            return ""
        
        full_context = "# MEMORY CONTEXT\n\n"
        full_context += "You have access to persistent memory from previous interactions:\n\n"
        full_context += "\n\n".join(context_parts)
        full_context += "\n\n---\n\n"
        
        return full_context
    
    def get_memory_stats(self) -> Dict[str, int]:
        """
        Get memory statistics.
        
        Returns:
            Dict with counts of stored items
        """
        summary = get_memory_summary(self.spec_dir)
        
        return {
            "conversations": summary.get("total_sessions", 0),
            "files_mapped": summary.get("total_files_mapped", 0),
            "patterns": summary.get("total_patterns", 0),
            "gotchas": summary.get("total_gotchas", 0)
        }
    
    def clear_all(self):
        """Clear all memory (use with caution!)"""
        from memory import clear_memory
        clear_memory(self.spec_dir)


# Global memory instance (initialized in main.py)
_memory_instance: Optional[AgentMemory] = None


def get_memory(working_dir: str) -> AgentMemory:
    """
    Get or create the global memory instance.
    
    Args:
        working_dir: Current working directory
    
    Returns:
        AgentMemory instance
    """
    global _memory_instance
    if _memory_instance is None or _memory_instance.working_dir != Path(working_dir):
        _memory_instance = AgentMemory(working_dir)
    return _memory_instance