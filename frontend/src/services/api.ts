// API service for ExamEye Shield backend communication

const API_URL = import.meta.env.VITE_BACKEND_URL || import.meta.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';

// Debug: Log API URL
console.log('🔗 API URL:', API_URL);

// Types
export interface Student {
  id: string;
  student_id: string;
  name: string;
  email: string;
  registered_at: string;
}

export interface ExamSession {
  id: string;
  student_id: string;
  student_name: string;
  start_time: string;
  end_time?: string;
  status: string;
  calibrated_pitch: number;
  calibrated_yaw: number;
  total_frames: number;
  violation_count: number;
}

export interface Violation {
  id: string;
  session_id: string;
  student_id: string;
  student_name: string;
  timestamp: string;
  violation_type: string;
  severity: string;
  message: string;
  snapshot_url?: string;
  head_pose?: any;
}

export interface CalibrationResult {
  success: boolean;
  pitch?: number;
  yaw?: number;
  message: string;
}

export interface FrameProcessResult {
  timestamp: string;
  violations: Array<{
    type: string;
    severity: string;
    message: string;
  }>;
  head_pose?: any;
  face_count: number;
  looking_away: boolean;
  multiple_faces: boolean;
  no_person: boolean;
  phone_detected: boolean;
  book_detected: boolean;
  snapshot_base64?: string;
}

// API Functions
export const api = {
  // Student endpoints
  registerStudent: async (name: string, email: string): Promise<Student> => {
    const response = await fetch(`${API_URL}/api/students/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, email }),
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Registration failed');
    }
    return response.json();
  },

  getStudent: async (studentId: string): Promise<Student> => {
    const response = await fetch(`${API_URL}/api/students/${studentId}`);
    if (!response.ok) throw new Error('Student not found');
    return response.json();
  },

  // Calibration
  calibrate: async (frameBase64: string): Promise<CalibrationResult> => {
    const response = await fetch(`${API_URL}/api/proctoring/calibrate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ frame_base64: frameBase64 }),
    });
    return response.json();
  },

  // Environment check
  checkEnvironment: async (frameBase64: string): Promise<any> => {
    const response = await fetch(`${API_URL}/api/proctoring/environment-check`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ frame_base64: frameBase64 }),
    });
    return response.json();
  },

  // Session endpoints
  startSession: async (
    studentId: string,
    studentName: string,
    calibratedPitch: number,
    calibratedYaw: number
  ): Promise<ExamSession> => {
    const response = await fetch(`${API_URL}/api/sessions/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        student_id: studentId,
        student_name: studentName,
        calibrated_pitch: calibratedPitch,
        calibrated_yaw: calibratedYaw,
      }),
    });
    if (!response.ok) throw new Error('Failed to start session');
    return response.json();
  },

  endSession: async (sessionId: string): Promise<void> => {
    const response = await fetch(`${API_URL}/api/sessions/${sessionId}/end`, {
      method: 'PUT',
    });
    if (!response.ok) throw new Error('Failed to end session');
  },

  getSession: async (sessionId: string): Promise<ExamSession> => {
    const response = await fetch(`${API_URL}/api/sessions/${sessionId}`);
    if (!response.ok) throw new Error('Session not found');
    return response.json();
  },

  getActiveSessions: async (): Promise<ExamSession[]> => {
    const response = await fetch(`${API_URL}/api/sessions/active/list`);
    return response.json();
  },

  getAllSessions: async (): Promise<ExamSession[]> => {
    const response = await fetch(`${API_URL}/api/admin/sessions/all`);
    return response.json();
  },

  // Frame processing (main proctoring endpoint)
  processFrame: async (
    sessionId: string,
    frameBase64: string,
    calibratedPitch: number,
    calibratedYaw: number
  ): Promise<FrameProcessResult> => {
    const response = await fetch(`${API_URL}/api/proctoring/process-frame`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        frame_base64: frameBase64,
        calibrated_pitch: calibratedPitch,
        calibrated_yaw: calibratedYaw,
      }),
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Frame processing failed');
    }
    return response.json();
  },

  // Violation endpoints
  getSessionViolations: async (sessionId: string): Promise<Violation[]> => {
    const response = await fetch(`${API_URL}/api/violations/session/${sessionId}`);
    return response.json();
  },

  getStudentViolations: async (studentId: string): Promise<Violation[]> => {
    const response = await fetch(`${API_URL}/api/violations/student/${studentId}`);
    return response.json();
  },

  getRecentViolations: async (limit: number = 50): Promise<Violation[]> => {
    const response = await fetch(`${API_URL}/api/violations/recent?limit=${limit}`);
    return response.json();
  },

  // Admin stats
  getAdminStats: async (): Promise<any> => {
    const response = await fetch(`${API_URL}/api/admin/stats`);
    return response.json();
  },

  // Browser violation reporting
  reportBrowserViolation: async (
    sessionId: string,
    violationType: string,
    message: string
  ): Promise<any> => {
    const response = await fetch(`${API_URL}/api/proctoring/browser-violation`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        violation_type: violationType,
        message: message,
      }),
    });
    if (!response.ok) throw new Error('Failed to report browser violation');
    return response.json();
  },

  // Statistics endpoints
  getAverageStatistics: async (): Promise<any> => {
    const response = await fetch(`${API_URL}/api/admin/statistics/average`);
    return response.json();
  },

  getStudentStatistics: async (studentId: string): Promise<any> => {
    const response = await fetch(`${API_URL}/api/admin/statistics/student/${studentId}`);
    return response.json();
  },

  getViolationsTimeline: async (limit: number = 100): Promise<any> => {
    const response = await fetch(`${API_URL}/api/admin/violations/timeline?limit=${limit}`);
    return response.json();
  },

  // Student evidence
  getStudentEvidence: async (studentId: string): Promise<any> => {
    const response = await fetch(`${API_URL}/api/admin/student/${studentId}/evidence`);
    return response.json();
  },

  // Students with violations
  getStudentsWithViolations: async (): Promise<any> => {
    const response = await fetch(`${API_URL}/api/admin/students-with-violations`);
    return response.json();
  },

  // Export endpoints
  exportStudentViolationsCSV: (studentId: string): string => {
    return `${API_URL}/api/admin/export/student/${studentId}/violations/csv`;
  },

  exportStudentReportHTML: (studentId: string): string => {
    return `${API_URL}/api/admin/export/student/${studentId}/report/html`;
  },
  exportViolationsCSV: (sessionId?: string, studentId?: string): string => {
    const params = new URLSearchParams();
    if (sessionId) params.append('session_id', sessionId);
    if (studentId) params.append('student_id', studentId);
    return `${API_URL}/api/admin/export/violations/csv?${params.toString()}`;
  },

  exportSummaryCSV: (): string => {
    return `${API_URL}/api/admin/export/summary/csv`;
  },

  exportReportHTML: (): string => {
    return `${API_URL}/api/admin/export/report/html`;
  },

  // Admin authentication
  adminLogin: async (username: string, password: string): Promise<any> => {
    const response = await fetch(`${API_URL}/api/admin/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Login failed');
    }
    return response.json();
  },

  // Health check
  healthCheck: async (): Promise<any> => {
    const response = await fetch(`${API_URL}/api/health`);
    return response.json();
  },
};

// WebSocket connection helper
export const createWebSocket = (path: string): WebSocket => {
  const wsUrl = API_URL.replace('https://', 'wss://').replace('http://', 'ws://');
  return new WebSocket(`${wsUrl}${path}`);
};
