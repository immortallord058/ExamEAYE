from fastapi import WebSocket
from typing import Dict, List, Set
import json
from datetime import datetime

class WebSocketManager:
    """
    Manages WebSocket connections for real-time admin dashboard updates
    """
    
    def __init__(self):
        # Store active admin connections
        self.admin_connections: List[WebSocket] = []
        
        # Store student connections by session_id
        self.student_connections: Dict[str, WebSocket] = {}
        
        # Track active sessions
        self.active_sessions: Set[str] = set()
    
    async def connect_admin(self, websocket: WebSocket):
        """
        Connect an admin to receive real-time updates
        """
        await websocket.accept()
        self.admin_connections.append(websocket)
        print(f"✅ Admin connected. Total admins: {len(self.admin_connections)}")
        
        # Send current active sessions count
        await self.send_to_admin({
            'type': 'connection_status',
            'data': {
                'active_sessions': len(self.active_sessions),
                'connected_admins': len(self.admin_connections)
            }
        })
    
    def disconnect_admin(self, websocket: WebSocket):
        """
        Disconnect an admin
        """
        if websocket in self.admin_connections:
            self.admin_connections.remove(websocket)
        print(f"❌ Admin disconnected. Remaining admins: {len(self.admin_connections)}")
    
    async def connect_student(self, session_id: str, websocket: WebSocket):
        """
        Connect a student for their exam session
        """
        await websocket.accept()
        self.student_connections[session_id] = websocket
        self.active_sessions.add(session_id)
        print(f"✅ Student connected. Session: {session_id}")
        
        # Notify admins about new session
        await self.broadcast_to_admins({
            'type': 'session_started',
            'data': {
                'session_id': session_id,
                'timestamp': datetime.utcnow().isoformat(),
                'total_active': len(self.active_sessions)
            }
        })
    
    def disconnect_student(self, session_id: str):
        """
        Disconnect a student
        """
        if session_id in self.student_connections:
            del self.student_connections[session_id]
        
        if session_id in self.active_sessions:
            self.active_sessions.remove(session_id)
        
        print(f"❌ Student disconnected. Session: {session_id}")
    
    async def send_to_admin(self, message: dict):
        """
        Send message to a single admin (used internally)
        """
        if self.admin_connections:
            await self.admin_connections[0].send_json(message)
    
    async def broadcast_to_admins(self, message: dict):
        """
        Broadcast message to all connected admins
        """
        dead_connections = []
        
        for connection in self.admin_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                print(f"Error sending to admin: {e}")
                dead_connections.append(connection)
        
        # Clean up dead connections
        for conn in dead_connections:
            self.disconnect_admin(conn)
    
    async def send_to_student(self, session_id: str, message: dict):
        """
        Send message to a specific student
        """
        if session_id in self.student_connections:
            try:
                await self.student_connections[session_id].send_json(message)
            except Exception as e:
                print(f"Error sending to student {session_id}: {e}")
                self.disconnect_student(session_id)
    
    async def broadcast_violation_alert(self, violation_data: dict):
        """
        Broadcast violation alert to all admins
        """
        message = {
            'type': 'violation_alert',
            'data': violation_data,
            'timestamp': datetime.utcnow().isoformat()
        }
        await self.broadcast_to_admins(message)
        print(f"🚨 Violation alert broadcasted: {violation_data.get('violation_type')}")
    
    async def send_session_update(self, session_data: dict):
        """
        Send session status update to admins
        """
        message = {
            'type': 'session_update',
            'data': session_data,
            'timestamp': datetime.utcnow().isoformat()
        }
        await self.broadcast_to_admins(message)
    
    async def send_student_warning(self, session_id: str, warning_message: str):
        """
        Send warning to student about violation
        """
        message = {
            'type': 'violation_warning',
            'data': {
                'message': warning_message,
                'timestamp': datetime.utcnow().isoformat()
            }
        }
        await self.send_to_student(session_id, message)
    
    def get_active_sessions_count(self) -> int:
        """
        Get count of active exam sessions
        """
        return len(self.active_sessions)
    
    def get_connected_admins_count(self) -> int:
        """
        Get count of connected admins
        """
        return len(self.admin_connections)

# Global WebSocket manager instance
ws_manager = WebSocketManager()
