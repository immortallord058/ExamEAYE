"""
Supabase Database Service
Handles PostgreSQL database operations via Supabase
"""
import os
from supabase import create_client, Client
from typing import Optional, List, Dict
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class SupabaseDBService:
    def __init__(self):
        supabase_url = os.environ.get('SUPABASE_URL')
        supabase_key = os.environ.get('SUPABASE_KEY')
        
        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set")
        
        self.client: Client = create_client(supabase_url, supabase_key)
        logger.info("Supabase database client initialized")
    
    # Student operations
    async def create_student(self, student_data: Dict) -> Dict:
        """Create a new student record"""
        try:
            result = self.client.table('students').insert(student_data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error creating student: {e}")
            raise
    
    async def get_student_by_id(self, student_id: str) -> Optional[Dict]:
        """Get student by student_id"""
        try:
            result = self.client.table('students').select('*').eq('student_id', student_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error getting student: {e}")
            return None
    
    async def get_all_students(self) -> List[Dict]:
        """Get all students"""
        try:
            result = self.client.table('students').select('*').execute()
            return result.data or []
        except Exception as e:
            logger.error(f"Error getting students: {e}")
            return []
    
    # Session operations
    async def create_session(self, session_data: Dict) -> Dict:
        """Create a new exam session"""
        try:
            result = self.client.table('sessions').insert(session_data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error creating session: {e}")
            raise
    
    async def get_session(self, session_id: str) -> Optional[Dict]:
        """Get session by ID"""
        try:
            result = self.client.table('sessions').select('*').eq('id', session_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error getting session: {e}")
            return None
    
    async def update_session(self, session_id: str, updates: Dict) -> bool:
        """Update session data"""
        try:
            self.client.table('sessions').update(updates).eq('id', session_id).execute()
            return True
        except Exception as e:
            logger.error(f"Error updating session: {e}")
            return False
    
    async def get_active_sessions(self) -> List[Dict]:
        """Get all active sessions"""
        try:
            result = self.client.table('sessions').select('*').eq('status', 'active').execute()
            return result.data or []
        except Exception as e:
            logger.error(f"Error getting active sessions: {e}")
            return []
    
    async def get_all_sessions(self) -> List[Dict]:
        """Get all sessions"""
        try:
            result = self.client.table('sessions').select('*').order('start_time', desc=True).execute()
            return result.data or []
        except Exception as e:
            logger.error(f"Error getting all sessions: {e}")
            return []
    
    # Violation operations
    async def create_violation(self, violation_data: Dict) -> Dict:
        """Create a new violation record"""
        try:
            result = self.client.table('violations').insert(violation_data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error creating violation: {e}")
            raise
    
    async def get_session_violations(self, session_id: str) -> List[Dict]:
        """Get all violations for a session"""
        try:
            result = self.client.table('violations').select('*').eq('session_id', session_id).order('timestamp', desc=True).execute()
            return result.data or []
        except Exception as e:
            logger.error(f"Error getting session violations: {e}")
            return []
    
    async def get_student_violations(self, student_id: str) -> List[Dict]:
        """Get all violations for a student"""
        try:
            result = self.client.table('violations').select('*').eq('student_id', student_id).order('timestamp', desc=True).execute()
            return result.data or []
        except Exception as e:
            logger.error(f"Error getting student violations: {e}")
            return []
    
    async def get_recent_violations(self, limit: int = 50) -> List[Dict]:
        """Get recent violations across all sessions"""
        try:
            result = self.client.table('violations').select('*').order('timestamp', desc=True).limit(limit).execute()
            return result.data or []
        except Exception as e:
            logger.error(f"Error getting recent violations: {e}")
            return []
    
    async def get_all_violations(self) -> List[Dict]:
        """Get all violations"""
        try:
            result = self.client.table('violations').select('*').execute()
            return result.data or []
        except Exception as e:
            logger.error(f"Error getting all violations: {e}")
            return []
    
    # Statistics operations
    async def get_stats(self) -> Dict:
        """Get overall statistics"""
        try:
            # Get counts using Supabase
            sessions_result = self.client.table('sessions').select('*', count='exact').execute()
            active_sessions_result = self.client.table('sessions').select('*', count='exact').eq('status', 'active').execute()
            completed_sessions_result = self.client.table('sessions').select('*', count='exact').eq('status', 'completed').execute()
            violations_result = self.client.table('violations').select('*', count='exact').execute()
            
            return {
                'total_sessions': sessions_result.count or 0,
                'active_sessions': active_sessions_result.count or 0,
                'completed_sessions': completed_sessions_result.count or 0,
                'total_violations': violations_result.count or 0
            }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {
                'total_sessions': 0,
                'active_sessions': 0,
                'completed_sessions': 0,
                'total_violations': 0
            }

# Global instance
supabase_db = SupabaseDBService()
