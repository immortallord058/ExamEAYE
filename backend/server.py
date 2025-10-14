from fastapi import FastAPI, APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from typing import List, Optional
from datetime import datetime
import random
import string

# Import our custom modules
from models import (
    Student, StudentCreate, StudentResponse,
    ExamSession, ExamSessionCreate, ExamSessionUpdate,
    Violation, ViolationCreate,
    FrameProcessRequest, FrameProcessResponse,
    CalibrationRequest, CalibrationResponse,
    EnvironmentCheckRequest, EnvironmentCheck,
    SessionStats, StudentViolationSummary,
    BrowserViolationRequest, StudentStatistics, AverageStatistics, ViolationTimePoint
)
from proctoring_service import proctoring_service
from supabase_service import supabase_service
from websocket_manager import ws_manager

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app
app = FastAPI(title="ExamEye Shield API")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def generate_student_id() -> str:
    """Generate unique student ID (e.g., STU-ABC123)"""
    letters = ''.join(random.choices(string.ascii_uppercase, k=3))
    numbers = ''.join(random.choices(string.digits, k=3))
    return f"STU-{letters}{numbers}"


# ============================================================================
# STUDENT ENDPOINTS
# ============================================================================

@api_router.post("/students/register", response_model=StudentResponse)
async def register_student(student_data: StudentCreate):
    """Register a new student for the exam"""
    try:
        # Check if email already exists
        existing = await db.students.find_one({"email": student_data.email})
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Create student with auto-generated ID
        student = Student(
            student_id=generate_student_id(),
            name=student_data.name,
            email=student_data.email
        )
        
        await db.students.insert_one(student.dict())
        logger.info(f"Student registered: {student.student_id}")
        
        return StudentResponse(**student.dict())
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/students/{student_id}", response_model=StudentResponse)
async def get_student(student_id: str):
    """Get student details by student_id"""
    student = await db.students.find_one({"student_id": student_id})
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return StudentResponse(**student)


# ============================================================================
# CALIBRATION & ENVIRONMENT CHECK ENDPOINTS
# ============================================================================

@api_router.post("/proctoring/calibrate", response_model=CalibrationResponse)
async def calibrate_student(request: CalibrationRequest):
    """Calibrate student's head pose for looking away detection"""
    try:
        result = proctoring_service.calibrate_from_frame(request.frame_base64)
        
        if result:
            pitch, yaw = result
            return CalibrationResponse(
                success=True,
                pitch=pitch,
                yaw=yaw,
                message="Calibration successful"
            )
        else:
            return CalibrationResponse(
                success=False,
                message="No face detected. Please face the camera directly."
            )
    except Exception as e:
        logger.error(f"Calibration error: {e}")
        return CalibrationResponse(
            success=False,
            message=f"Calibration failed: {str(e)}"
        )


@api_router.post("/proctoring/environment-check", response_model=EnvironmentCheck)
async def check_environment(request: EnvironmentCheckRequest):
    """Check if environment is suitable for exam (lighting, face detection)"""
    try:
        result = proctoring_service.calibrate_from_frame(request.frame_base64)
        
        if result:
            return EnvironmentCheck(
                lighting_ok=True,
                face_detected=True,
                face_centered=True,
                message="Environment check passed. Ready to start exam."
            )
        else:
            return EnvironmentCheck(
                lighting_ok=False,
                face_detected=False,
                face_centered=False,
                message="Face not detected. Please adjust lighting and camera position."
            )
    except Exception as e:
        logger.error(f"Environment check error: {e}")
        return EnvironmentCheck(
            lighting_ok=False,
            face_detected=False,
            face_centered=False,
            message=f"Environment check failed: {str(e)}"
        )


# ============================================================================
# EXAM SESSION ENDPOINTS
# ============================================================================

@api_router.post("/sessions/start", response_model=ExamSession)
async def start_exam_session(session_data: ExamSessionCreate):
    """Start a new exam session"""
    try:
        session = ExamSession(
            student_id=session_data.student_id,
            student_name=session_data.student_name,
            calibrated_pitch=session_data.calibrated_pitch,
            calibrated_yaw=session_data.calibrated_yaw
        )
        
        await db.exam_sessions.insert_one(session.dict())
        logger.info(f"Exam session started: {session.id} for {session.student_name}")
        
        # Notify admins via WebSocket
        await ws_manager.send_session_update({
            'session_id': session.id,
            'student_id': session.student_id,
            'student_name': session.student_name,
            'status': 'started',
            'start_time': session.start_time.isoformat()
        })
        
        return session
    except Exception as e:
        logger.error(f"Session start error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/sessions/{session_id}", response_model=ExamSession)
async def get_session(session_id: str):
    """Get exam session details"""
    session = await db.exam_sessions.find_one({"id": session_id})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return ExamSession(**session)


@api_router.put("/sessions/{session_id}/end")
async def end_exam_session(session_id: str):
    """End an exam session"""
    try:
        session = await db.exam_sessions.find_one({"id": session_id})
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        await db.exam_sessions.update_one(
            {"id": session_id},
            {"$set": {
                "end_time": datetime.utcnow(),
                "status": "completed"
            }}
        )
        
        # Notify admins
        await ws_manager.send_session_update({
            'session_id': session_id,
            'status': 'completed',
            'end_time': datetime.utcnow().isoformat()
        })
        
        return {"message": "Session ended successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Session end error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/sessions/active/list", response_model=List[ExamSession])
async def get_active_sessions():
    """Get all active exam sessions"""
    sessions = await db.exam_sessions.find({"status": "active"}).to_list(100)
    return [ExamSession(**session) for session in sessions]


# ============================================================================
# PROCTORING - FRAME PROCESSING ENDPOINT
# ============================================================================

@api_router.post("/proctoring/process-frame", response_model=FrameProcessResponse)
async def process_frame(request: FrameProcessRequest):
    """Process a video frame for violations"""
    try:
        # Process frame with AI
        result = proctoring_service.process_frame(
            request.frame_base64,
            request.calibrated_pitch,
            request.calibrated_yaw
        )
        
        if 'error' in result:
            raise HTTPException(status_code=400, detail=result['error'])
        
        # Update session frame count
        await db.exam_sessions.update_one(
            {"id": request.session_id},
            {"$inc": {"total_frames": 1}}
        )
        
        # If violations detected, save to database and Supabase
        if result['violations']:
            session = await db.exam_sessions.find_one({"id": request.session_id})
            
            for violation_detail in result['violations']:
                # Upload snapshot to Supabase if available
                snapshot_url = None
                if result.get('snapshot_base64'):
                    snapshot_url = supabase_service.upload_violation_snapshot(
                        result['snapshot_base64'],
                        session['student_id'],
                        request.session_id,
                        violation_detail['type']
                    )
                
                # Create violation record
                violation = Violation(
                    session_id=request.session_id,
                    student_id=session['student_id'],
                    student_name=session['student_name'],
                    violation_type=violation_detail['type'],
                    severity=violation_detail['severity'],
                    message=violation_detail['message'],
                    snapshot_url=snapshot_url,
                    head_pose=result.get('head_pose')
                )
                
                await db.violations.insert_one(violation.dict())
                
                # Update session violation count
                await db.exam_sessions.update_one(
                    {"id": request.session_id},
                    {"$inc": {"violation_count": 1}}
                )
                
                # Broadcast violation alert to admins via WebSocket
                await ws_manager.broadcast_violation_alert({
                    'session_id': request.session_id,
                    'student_id': session['student_id'],
                    'student_name': session['student_name'],
                    'violation_type': violation_detail['type'],
                    'severity': violation_detail['severity'],
                    'message': violation_detail['message'],
                    'snapshot_url': snapshot_url,
                    'timestamp': violation.timestamp.isoformat()
                })
                
                logger.info(f"Violation detected: {violation_detail['type']} - {session['student_name']}")
        
        return FrameProcessResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Frame processing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# VIOLATION ENDPOINTS
# ============================================================================

@api_router.get("/violations/session/{session_id}", response_model=List[Violation])
async def get_session_violations(session_id: str):
    """Get all violations for a specific session"""
    violations = await db.violations.find({"session_id": session_id}).to_list(1000)
    return [Violation(**v) for v in violations]


@api_router.get("/violations/student/{student_id}", response_model=List[Violation])
async def get_student_violations(student_id: str):
    """Get all violations for a specific student"""
    violations = await db.violations.find({"student_id": student_id}).to_list(1000)
    return [Violation(**v) for v in violations]


@api_router.get("/violations/recent", response_model=List[Violation])
async def get_recent_violations(limit: int = 50):
    """Get recent violations across all sessions"""
    violations = await db.violations.find().sort("timestamp", -1).limit(limit).to_list(limit)
    return [Violation(**v) for v in violations]


# ============================================================================
# ADMIN DASHBOARD ENDPOINTS
# ============================================================================

@api_router.get("/admin/stats", response_model=SessionStats)
async def get_admin_stats():
    """Get overall statistics for admin dashboard"""
    try:
        total_sessions = await db.exam_sessions.count_documents({})
        active_sessions = await db.exam_sessions.count_documents({"status": "active"})
        completed_sessions = await db.exam_sessions.count_documents({"status": "completed"})
        total_violations = await db.violations.count_documents({})
        
        return SessionStats(
            total_sessions=total_sessions,
            active_sessions=active_sessions,
            completed_sessions=completed_sessions,
            total_violations=total_violations
        )
    except Exception as e:
        logger.error(f"Stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/admin/sessions/all", response_model=List[ExamSession])
async def get_all_sessions():
    """Get all exam sessions"""
    sessions = await db.exam_sessions.find().sort("start_time", -1).to_list(1000)
    return [ExamSession(**session) for session in sessions]


# ============================================================================
# WEBSOCKET ENDPOINTS
# ============================================================================

@app.websocket("/ws/admin")
async def websocket_admin(websocket: WebSocket):
    """WebSocket endpoint for admin dashboard real-time updates"""
    await ws_manager.connect_admin(websocket)
    try:
        while True:
            # Keep connection alive and receive messages
            data = await websocket.receive_text()
            # Admin can send commands if needed
    except WebSocketDisconnect:
        ws_manager.disconnect_admin(websocket)


@app.websocket("/ws/student/{session_id}")
async def websocket_student(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for student exam session"""
    await ws_manager.connect_student(session_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle student messages if needed
    except WebSocketDisconnect:
        ws_manager.disconnect_student(session_id)


# ============================================================================
# BASIC ROUTES
# ============================================================================

@api_router.get("/")
async def root():
    return {
        "message": "ExamEye Shield API",
        "version": "1.0.0",
        "status": "active"
    }


@api_router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "active_sessions": ws_manager.get_active_sessions_count()
    }


# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
