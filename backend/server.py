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
from export_service import export_service
from fastapi.responses import StreamingResponse, HTMLResponse

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
                # Only upload snapshots for camera-based violations
                # Browser events (copy_paste, tab_switch, excessive_noise) don't need snapshots
                camera_based_violations = ['phone_detected', 'book_detected', 'multiple_faces', 
                                          'no_person', 'looking_away']
                
                snapshot_url = None
                snapshot_base64 = None
                
                if violation_detail['type'] in camera_based_violations and result.get('snapshot_base64'):
                    logger.info(f"Uploading snapshot for violation: {violation_detail['type']}")
                    snapshot_url = supabase_service.upload_violation_snapshot(
                        result['snapshot_base64'],
                        session['student_id'],
                        request.session_id,
                        violation_detail['type']
                    )
                    # Always keep base64 as fallback
                    snapshot_base64 = result['snapshot_base64']
                    if not snapshot_url:
                        logger.warning("Supabase upload failed, using base64 fallback for display")
                    else:
                        logger.info(f"✅ Snapshot uploaded successfully: {snapshot_url}")
                else:
                    logger.info(f"Skipping snapshot for browser/audio violation: {violation_detail['type']}")
                
                # Create violation record
                violation = Violation(
                    session_id=request.session_id,
                    student_id=session['student_id'],
                    student_name=session['student_name'],
                    violation_type=violation_detail['type'],
                    severity=violation_detail['severity'],
                    message=violation_detail['message'],
                    snapshot_url=snapshot_url,
                    snapshot_base64=snapshot_base64,
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


@api_router.post("/proctoring/browser-violation")
async def report_browser_violation(request: BrowserViolationRequest):
    """Report browser-based violations (copy/paste, tab switching)"""
    try:
        session = await db.exam_sessions.find_one({"id": request.session_id})
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Create violation record
        violation = Violation(
            session_id=request.session_id,
            student_id=session['student_id'],
            student_name=session['student_name'],
            violation_type=request.violation_type,
            severity='medium',
            message=request.message,
            snapshot_url=None,  # No snapshot for browser violations
            head_pose=None
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
            'violation_type': request.violation_type,
            'severity': 'medium',
            'message': request.message,
            'snapshot_url': None,
            'timestamp': violation.timestamp.isoformat()
        })
        
        logger.info(f"Browser violation detected: {request.violation_type} - {session['student_name']}")
        
        return {"message": "Violation recorded", "violation_id": violation.id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Browser violation error: {e}")
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


@api_router.get("/admin/student/{student_id}/evidence")
async def get_student_evidence(student_id: str):
    """Get all violations with evidence for a specific student"""
    try:
        violations = await db.violations.find({"student_id": student_id}).sort("timestamp", -1).to_list(1000)
        
        # Filter violations that have snapshots
        evidence_violations = [v for v in violations if v.get('snapshot_url') or v.get('snapshot_base64')]
        
        return {
            "student_id": student_id,
            "total_violations": len(violations),
            "violations_with_evidence": len(evidence_violations),
            "evidence": evidence_violations
        }
    except Exception as e:
        logger.error(f"Get student evidence error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/violations/{violation_id}/snapshot")
async def get_violation_snapshot(violation_id: str):
    """Get violation snapshot image"""
    try:
        violation = await db.violations.find_one({"id": violation_id})
        if not violation:
            raise HTTPException(status_code=404, detail="Violation not found")
        
        # If Supabase URL exists, redirect to it
        if violation.get('snapshot_url'):
            from fastapi.responses import RedirectResponse
            return RedirectResponse(url=violation['snapshot_url'])
        
        # Otherwise return base64 image
        if violation.get('snapshot_base64'):
            import base64
            from fastapi.responses import Response
            
            # Remove data URI prefix if present
            image_data = violation['snapshot_base64']
            if ',' in image_data:
                image_data = image_data.split(',')[1]
            
            image_bytes = base64.b64decode(image_data)
            return Response(content=image_bytes, media_type="image/jpeg")
        
        raise HTTPException(status_code=404, detail="No snapshot available")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get snapshot error: {e}")
        raise HTTPException(status_code=500, detail=str(e))



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
    """Get admin dashboard statistics"""
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
        logger.error(f"Get admin stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/admin/login")
async def admin_login(credentials: dict):
    """
    Simple admin login endpoint
    In production, this should use proper authentication
    """
    username = credentials.get('username')
    password = credentials.get('password')
    
    # Simple hardcoded credentials (replace with proper auth in production)
    if username == "admin" and password == "vinay":
        return {
            "success": True,
            "message": "Login successful",
            "admin": {
                "username": "admin",
                "role": "administrator"
            }
        }
    
    raise HTTPException(status_code=401, detail="Invalid credentials")


@api_router.get("/admin/connectivity")
async def check_admin_connectivity():
    """Simple endpoint to check backend connectivity"""
    return {
        "status": "connected",
        "message": "Backend is reachable",
        "timestamp": datetime.utcnow().isoformat()
    }


@api_router.get("/admin/students-with-violations")
async def get_students_with_violations():
    """Get all students who have violations with their violation counts and latest snapshots"""
    try:
        # Get all violations grouped by student
        violations = await db.violations.find().to_list(10000)
        
        students_map = {}
        for v in violations:
            student_id = v.get('student_id')
            if student_id not in students_map:
                students_map[student_id] = {
                    'student_id': student_id,
                    'student_name': v.get('student_name'),
                    'violation_count': 0,
                    'latest_snapshot': None,
                    'violation_types': set()
                }
            
            students_map[student_id]['violation_count'] += 1
            students_map[student_id]['violation_types'].add(v.get('violation_type'))
            
            # Keep latest snapshot (without full base64 for performance)
            if v.get('snapshot_url'):
                if not students_map[student_id]['latest_snapshot']:
                    students_map[student_id]['latest_snapshot'] = v.get('snapshot_url')
            elif v.get('snapshot_base64') and not students_map[student_id]['latest_snapshot']:
                # Store truncated base64 for thumbnail
                snapshot = v.get('snapshot_base64')
                if len(snapshot) > 200:
                    snapshot = snapshot[:200]  # Truncate for performance
                students_map[student_id]['latest_snapshot'] = snapshot
        
        # Convert to list and format
        students_list = []
        for student_id, data in students_map.items():
            students_list.append({
                'student_id': student_id,
                'student_name': data['student_name'],
                'violation_count': data['violation_count'],
                'violation_types': list(data['violation_types']),
                'latest_snapshot': data['latest_snapshot']
            })
        
        # Sort by violation count descending
        students_list.sort(key=lambda x: x['violation_count'], reverse=True)
        
        return {"students": students_list}
    except Exception as e:
        logger.error(f"Get students with violations error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    raise HTTPException(status_code=401, detail="Invalid credentials")


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



@api_router.get("/admin/statistics/average", response_model=AverageStatistics)
async def get_average_statistics():
    """Get average statistics across all students"""
    try:
        # Get all students
        students = await db.students.find().to_list(1000)
        total_students = len(students)
        
        if total_students == 0:
            return AverageStatistics(
                avg_violations_per_student=0,
                avg_exam_duration_minutes=0,
                avg_violation_types={},
                total_students=0,
                total_sessions=0
            )
        
        # Get all sessions
        sessions = await db.exam_sessions.find().to_list(1000)
        total_sessions = len(sessions)
        
        # Calculate average violations per student
        total_violations = await db.violations.count_documents({})
        avg_violations_per_student = total_violations / total_students if total_students > 0 else 0
        
        # Calculate average exam duration
        total_duration_minutes = 0
        completed_sessions = 0
        for session in sessions:
            if session.get('end_time') and session.get('start_time'):
                duration = (session['end_time'] - session['start_time']).total_seconds() / 60
                total_duration_minutes += duration
                completed_sessions += 1
        
        avg_exam_duration_minutes = total_duration_minutes / completed_sessions if completed_sessions > 0 else 0
        
        # Calculate average violation types
        violations = await db.violations.find().to_list(10000)
        violation_type_counts = {}
        for v in violations:
            v_type = v.get('violation_type', 'unknown')
            violation_type_counts[v_type] = violation_type_counts.get(v_type, 0) + 1
        
        avg_violation_types = {
            v_type: count / total_students 
            for v_type, count in violation_type_counts.items()
        }
        
        return AverageStatistics(
            avg_violations_per_student=round(avg_violations_per_student, 2),
            avg_exam_duration_minutes=round(avg_exam_duration_minutes, 2),
            avg_violation_types=avg_violation_types,
            total_students=total_students,
            total_sessions=total_sessions
        )
    except Exception as e:
        logger.error(f"Average statistics error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/admin/statistics/student/{student_id}", response_model=StudentStatistics)
async def get_student_statistics(student_id: str):
    """Get detailed statistics for a specific student"""
    try:
        # Get student
        student = await db.students.find_one({"student_id": student_id})
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")
        
        # Get all sessions for this student
        sessions = await db.exam_sessions.find({"student_id": student_id}).to_list(1000)
        total_sessions = len(sessions)
        
        # Get all violations for this student
        violations = await db.violations.find({"student_id": student_id}).to_list(10000)
        total_violations = len(violations)
        
        # Calculate average violations per session
        avg_violations_per_session = total_violations / total_sessions if total_sessions > 0 else 0
        
        # Calculate average session duration
        total_duration_minutes = 0
        for session in sessions:
            if session.get('end_time') and session.get('start_time'):
                duration = (session['end_time'] - session['start_time']).total_seconds() / 60
                total_duration_minutes += duration
        
        avg_session_duration_minutes = total_duration_minutes / total_sessions if total_sessions > 0 else 0
        
        # Violation breakdown by type
        violation_breakdown = {}
        for v in violations:
            v_type = v.get('violation_type', 'unknown')
            violation_breakdown[v_type] = violation_breakdown.get(v_type, 0) + 1
        
        # Violations over time (grouped by hour)
        violations_by_time = {}
        for v in violations:
            timestamp = v.get('timestamp')
            if timestamp:
                # Group by hour
                hour_key = timestamp.replace(minute=0, second=0, microsecond=0)
                violations_by_time[hour_key] = violations_by_time.get(hour_key, 0) + 1
        
        violations_over_time = [
            ViolationTimePoint(timestamp=ts, count=count)
            for ts, count in sorted(violations_by_time.items())
        ]
        
        return StudentStatistics(
            student_id=student_id,
            student_name=student.get('name', 'Unknown'),
            total_violations=total_violations,
            avg_violations_per_session=round(avg_violations_per_session, 2),
            total_sessions=total_sessions,
            avg_session_duration_minutes=round(avg_session_duration_minutes, 2),
            violation_breakdown=violation_breakdown,
            violations_over_time=violations_over_time
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Student statistics error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/admin/export/student/{student_id}/violations/csv")
async def export_student_violations_csv(student_id: str):
    """Export individual student violations to CSV"""
    try:
        student = await db.students.find_one({"student_id": student_id})
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")
        
        violations = await db.violations.find({"student_id": student_id}).to_list(10000)
        
        csv_content = export_service.export_student_violations_csv(
            student_id,
            student.get('name', 'Unknown'),
            violations
        )
        
        return StreamingResponse(
            iter([csv_content]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=violations_{student_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Export student CSV error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/admin/export/student/{student_id}/report/html", response_class=HTMLResponse)
async def export_student_report_html(student_id: str):
    """Export individual student report as HTML with violation images"""
    try:
        student = await db.students.find_one({"student_id": student_id})
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")
        
        violations = await db.violations.find({"student_id": student_id}).sort("timestamp", -1).to_list(10000)
        
        html_content = export_service.generate_student_html_report(
            student_id,
            student.get('name', 'Unknown'),
            violations
        )
        
        return HTMLResponse(content=html_content)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Export student HTML error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

        violations = await db.violations.find({"student_id": student_id}).to_list(10000)
        total_violations = len(violations)
        
        # Calculate average violations per session
        avg_violations_per_session = total_violations / total_sessions if total_sessions > 0 else 0
        
        # Calculate average session duration
        total_duration_minutes = 0
        for session in sessions:
            if session.get('end_time') and session.get('start_time'):
                duration = (session['end_time'] - session['start_time']).total_seconds() / 60
                total_duration_minutes += duration
        
        avg_session_duration_minutes = total_duration_minutes / total_sessions if total_sessions > 0 else 0
        
        # Violation breakdown by type
        violation_breakdown = {}
        for v in violations:
            v_type = v.get('violation_type', 'unknown')
            violation_breakdown[v_type] = violation_breakdown.get(v_type, 0) + 1
        
        # Violations over time (grouped by hour)
        violations_by_time = {}
        for v in violations:
            timestamp = v.get('timestamp')
            if timestamp:
                # Group by hour
                hour_key = timestamp.replace(minute=0, second=0, microsecond=0)
                violations_by_time[hour_key] = violations_by_time.get(hour_key, 0) + 1
        
        violations_over_time = [
            ViolationTimePoint(timestamp=ts, count=count)
            for ts, count in sorted(violations_by_time.items())
        ]
        
        return StudentStatistics(
            student_id=student_id,
            student_name=student.get('name', 'Unknown'),
            total_violations=total_violations,
            avg_violations_per_session=round(avg_violations_per_session, 2),
            total_sessions=total_sessions,
            avg_session_duration_minutes=round(avg_session_duration_minutes, 2),
            violation_breakdown=violation_breakdown,
            violations_over_time=violations_over_time
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Student statistics error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/admin/violations/timeline")
async def get_violations_timeline(limit: int = 100):
    """Get violations timeline for line chart (all students)"""
    try:
        violations = await db.violations.find().sort("timestamp", 1).limit(limit).to_list(limit)
        
        # Group by time intervals (every 5 minutes)
        violations_by_time = {}
        for v in violations:
            timestamp = v.get('timestamp')
            if timestamp:
                # Round to 5-minute intervals
                minute = (timestamp.minute // 5) * 5
                time_key = timestamp.replace(minute=minute, second=0, microsecond=0)
                violations_by_time[time_key] = violations_by_time.get(time_key, 0) + 1
        
        timeline = [
            {"timestamp": ts.isoformat(), "count": count}
            for ts, count in sorted(violations_by_time.items())
        ]
        
        return {"timeline": timeline}
    except Exception as e:
        logger.error(f"Violations timeline error: {e}")
        raise HTTPException(status_code=500, detail=str(e))



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


@api_router.get("/admin/export/violations/csv")
async def export_violations_csv(session_id: Optional[str] = None, student_id: Optional[str] = None):
    """Export violations to CSV"""
    try:
        if session_id:
            violations = await db.violations.find({"session_id": session_id}).to_list(10000)
        elif student_id:
            violations = await db.violations.find({"student_id": student_id}).to_list(10000)
        else:
            violations = await db.violations.find().to_list(10000)
        
        csv_content = export_service.export_violations_csv(violations)
        
        return StreamingResponse(
            iter([csv_content]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=violations_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"}
        )
    except Exception as e:
        logger.error(f"Export CSV error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/admin/export/summary/csv")
async def export_summary_csv():
    """Export summary report to CSV"""
    try:
        sessions = await db.exam_sessions.find().to_list(10000)
        violations = await db.violations.find().to_list(10000)
        students = await db.students.find().to_list(10000)
        
        csv_content = export_service.export_summary_csv(sessions, violations, students)
        
        return StreamingResponse(
            iter([csv_content]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=exam_summary_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"}
        )
    except Exception as e:
        logger.error(f"Export summary CSV error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/admin/export/report/html", response_class=HTMLResponse)
async def export_report_html():
    """Export summary report as HTML (can be printed to PDF)"""
    try:
        sessions = await db.exam_sessions.find().to_list(10000)
        violations = await db.violations.find().to_list(10000)
        students = await db.students.find().to_list(10000)
        
        html_content = export_service.generate_html_report(sessions, violations, students)
        
        return HTMLResponse(content=html_content)
    except Exception as e:
        logger.error(f"Export HTML error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
