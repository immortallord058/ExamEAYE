import cv2
import mediapipe as mp
import numpy as np
from ultralytics import YOLO
import base64
from typing import Dict, Optional, Tuple
import time
from datetime import datetime

class ProctoringService:
    """
    AI-powered proctoring service using MediaPipe and YOLOv8n
    Detects: looking away, multiple people, prohibited objects (phone, book)
    """
    
    def __init__(self):
        # Initialize MediaPipe
        self.mp_face_mesh = mp.solutions.face_mesh.FaceMesh(
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.mp_face_detection = mp.solutions.face_detection.FaceDetection(
            min_detection_confidence=0.5
        )
        
        # Initialize YOLO model with optimized settings
        self.yolo_model = YOLO('models/yolov8n.pt')
        self.yolo_model.conf = 0.45  # Confidence threshold
        
        # 3D Model points for head pose estimation
        self.model_points = np.array([
            (0.0, 0.0, 0.0),
            (0.0, -330.0, -65.0),
            (-225.0, 170.0, -135.0),
            (225.0, 170.0, -135.0),
            (-150.0, -150.0, -125.0),
            (150.0, -150.0, -125.0)
        ], dtype=np.float64)
        
        # Thresholds (increased by 35% for leniency)
        self.MAX_YAW_OFFSET = 110 * 1.35
        self.MAX_PITCH_OFFSET = 140 * 1.35
        
        # Detection confidence thresholds
        self.OBJECT_CONFIDENCE_THRESHOLD = 0.45
        self.FACE_CONFIDENCE_THRESHOLD = 0.5
        
    def estimate_head_pose(self, landmarks, width: int, height: int) -> Optional[Tuple[float, float, float]]:
        """
        Estimate head pose (pitch, yaw, roll) from facial landmarks
        """
        try:
            image_points = np.array([
                (landmarks[1].x * width, landmarks[1].y * height),
                (landmarks[152].x * width, landmarks[152].y * height),
                (landmarks[33].x * width, landmarks[33].y * height),
                (landmarks[263].x * width, landmarks[263].y * height),
                (landmarks[61].x * width, landmarks[61].y * height),
                (landmarks[291].x * width, landmarks[291].y * height)
            ], dtype=np.float64)

            focal_length = width
            camera_matrix = np.array([
                [focal_length, 0, width / 2],
                [0, focal_length, height / 2],
                [0, 0, 1]
            ], dtype=np.float64)

            success, rotation_vector, _ = cv2.solvePnP(
                self.model_points, 
                image_points, 
                camera_matrix, 
                np.zeros((4, 1))
            )
            
            if not success:
                return None

            rmat, _ = cv2.Rodrigues(rotation_vector)
            angles, _, _, _, _, _ = cv2.RQDecomp3x3(rmat)
            return angles  # pitch, yaw, roll
        except Exception as e:
            print(f"Head pose estimation error: {e}")
            return None

    def is_looking_away(self, pitch: float, yaw: float, calibrated_pitch: float, calibrated_yaw: float) -> bool:
        """
        Check if user is looking away from camera based on calibrated values
        """
        pitch_offset = abs(pitch - calibrated_pitch)
        yaw_offset = abs(yaw - calibrated_yaw)
        return pitch_offset > self.MAX_PITCH_OFFSET or yaw_offset > self.MAX_YAW_OFFSET

    def detect_multiple_faces(self, detections) -> bool:
        """
        Check if multiple faces are detected
        """
        return len(detections) > 1 if detections else False

    def detect_prohibited_objects(self, frame: np.ndarray) -> Dict[str, any]:
        """
        Detect prohibited objects (cell phone, book) using YOLOv8
        Returns dict with detection info and annotated frame
        """
        detections = {
            'phone_detected': False,
            'book_detected': False,
            'objects': []
        }
        
        try:
            # Run YOLO detection with confidence threshold
            yolo_results = self.yolo_model(
                frame, 
                stream=True, 
                verbose=False,
                conf=self.OBJECT_CONFIDENCE_THRESHOLD
            )
            
            for result in yolo_results:
                if result.boxes is None or len(result.boxes) == 0:
                    continue
                    
                for box in result.boxes:
                    cls = result.names[int(box.cls[0])]
                    confidence = float(box.conf[0])
                    
                    # Only process if confidence meets threshold
                    if confidence < self.OBJECT_CONFIDENCE_THRESHOLD:
                        continue
                    
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    
                    # Detect cell phone (including variations)
                    if cls in ["cell phone", "phone", "mobile"]:
                        detections['objects'].append({
                            'type': 'cell phone',
                            'confidence': confidence,
                            'bbox': [x1, y1, x2, y2]
                        })
                        detections['phone_detected'] = True
                        
                        # Draw bounding box
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 3)
                        cv2.putText(frame, f"PHONE {confidence:.2f}", (x1, y1 - 10),
                                  cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                    
                    # Detect book
                    elif cls == "book":
                        detections['objects'].append({
                            'type': 'book',
                            'confidence': confidence,
                            'bbox': [x1, y1, x2, y2]
                        })
                        detections['book_detected'] = True
                        
                        # Draw bounding box
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 3)
                        cv2.putText(frame, f"BOOK {confidence:.2f}", (x1, y1 - 10),
                                  cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
        except Exception as e:
            print(f"Object detection error: {e}")
        
        detections['annotated_frame'] = frame
        return detections

    def process_frame(self, frame_base64: str, calibrated_pitch: float, calibrated_yaw: float) -> Dict:
        """
        Process a single frame for all violations
        Returns comprehensive violation report
        """
        try:
            # Decode base64 frame
            frame_data = base64.b64decode(frame_base64.split(',')[1] if ',' in frame_base64 else frame_base64)
            nparr = np.frombuffer(frame_data, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if frame is None:
                return {'error': 'Invalid frame data'}
            
            height, width, _ = frame.shape
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Initialize result
            result = {
                'timestamp': datetime.utcnow().isoformat(),
                'violations': [],
                'head_pose': None,
                'face_count': 0,
                'looking_away': False,
                'multiple_faces': False,
                'no_person': False,
                'phone_detected': False,
                'book_detected': False,
                'snapshot_base64': None
            }
            
            # Detect multiple faces first
            face_detection_results = self.mp_face_detection.process(rgb_frame)
            if face_detection_results.detections:
                result['face_count'] = len(face_detection_results.detections)
                
                if self.detect_multiple_faces(face_detection_results.detections):
                    result['multiple_faces'] = True
                    result['violations'].append({
                        'type': 'multiple_faces',
                        'severity': 'high',
                        'message': f'{len(face_detection_results.detections)} people detected in frame'
                    })
                    cv2.putText(frame, "MULTIPLE PEOPLE DETECTED!", (50, 100),
                              cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            else:
                # No person detected
                result['no_person'] = True
                result['violations'].append({
                    'type': 'no_person',
                    'severity': 'high',
                    'message': 'No person detected in frame'
                })
                cv2.putText(frame, "NO PERSON DETECTED!", (50, 50),
                          cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            
            # Process face mesh for head pose (only if single person detected)
            if result['face_count'] == 1:
                face_mesh_results = self.mp_face_mesh.process(rgb_frame)
                if face_mesh_results.multi_face_landmarks:
                    landmarks = face_mesh_results.multi_face_landmarks[0].landmark
                    angles = self.estimate_head_pose(landmarks, width, height)
                    
                    if angles:
                        pitch, yaw, roll = angles
                        result['head_pose'] = {
                            'pitch': float(pitch),
                            'yaw': float(yaw),
                            'roll': float(roll)
                        }
                        
                        # Check if looking away
                        if self.is_looking_away(pitch, yaw, calibrated_pitch, calibrated_yaw):
                            result['looking_away'] = True
                            result['violations'].append({
                                'type': 'looking_away',
                                'severity': 'medium',
                                'message': 'Student is looking away from screen'
                            })
                            cv2.putText(frame, "LOOKING AWAY!", (50, 150), 
                                      cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            
            # Detect prohibited objects
            object_detection = self.detect_prohibited_objects(frame)
            result['phone_detected'] = object_detection['phone_detected']
            result['book_detected'] = object_detection['book_detected']
            
            if object_detection['phone_detected']:
                result['violations'].append({
                    'type': 'phone_detected',
                    'severity': 'high',
                    'message': 'Mobile phone detected'
                })
            
            if object_detection['book_detected']:
                result['violations'].append({
                    'type': 'book_detected',
                    'severity': 'medium',
                    'message': 'Book detected'
                })
            
            # If violations exist, capture snapshot
            if result['violations']:
                annotated_frame = object_detection['annotated_frame']
                _, buffer = cv2.imencode('.jpg', annotated_frame)
                result['snapshot_base64'] = base64.b64encode(buffer).decode('utf-8')
            
            return result
            
        except Exception as e:
            return {'error': f'Frame processing error: {str(e)}'}

    def calibrate_from_frame(self, frame_base64: str) -> Optional[Tuple[float, float]]:
        """
        Extract calibration values (pitch, yaw) from a frame
        """
        try:
            # Decode base64 frame
            frame_data = base64.b64decode(frame_base64.split(',')[1] if ',' in frame_base64 else frame_base64)
            nparr = np.frombuffer(frame_data, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if frame is None:
                return None
            
            height, width, _ = frame.shape
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            face_mesh_results = self.mp_face_mesh.process(rgb_frame)
            if face_mesh_results.multi_face_landmarks:
                landmarks = face_mesh_results.multi_face_landmarks[0].landmark
                angles = self.estimate_head_pose(landmarks, width, height)
                
                if angles:
                    pitch, yaw, _ = angles
                    return (float(pitch), float(yaw))
            
            return None
        except Exception as e:
            print(f"Calibration error: {e}")
            return None

# Global instance
proctoring_service = ProctoringService()
