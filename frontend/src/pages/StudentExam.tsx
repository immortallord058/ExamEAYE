import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { Shield, Camera, AlertTriangle, Eye, User2, Smartphone, Book, Clock, LogOut } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import { api, ExamSession, createWebSocket } from "@/services/api";
import { startWebcam, stopWebcam, captureFrame } from "@/utils/webcam";

const StudentExam = () => {
  const navigate = useNavigate();
  const [studentData, setStudentData] = useState<any>(null);
  const [calibrationData, setCalibrationData] = useState<any>(null);
  const [session, setSession] = useState<ExamSession | null>(null);
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [isMonitoring, setIsMonitoring] = useState(false);
  const [currentViolations, setCurrentViolations] = useState<string[]>([]);
  const [violationCount, setViolationCount] = useState(0);
  const [examTime, setExamTime] = useState(0);
  const [warnings, setWarnings] = useState<Array<{ type: string; message: string; time: string }>>([]);
  
  const videoRef = useRef<HTMLVideoElement>(null);
  const monitoringInterval = useRef<NodeJS.Timeout | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    // Load student and calibration data
    const studentDataStr = sessionStorage.getItem('studentData');
    const calibDataStr = sessionStorage.getItem('calibrationData');

    if (!studentDataStr || !calibDataStr) {
      toast.error("Please complete registration and verification first");
      navigate('/student/register');
      return;
    }

    setStudentData(JSON.parse(studentDataStr));
    setCalibrationData(JSON.parse(calibDataStr));

    return () => {
      cleanup();
    };
  }, [navigate]);

  useEffect(() => {
    // Start exam session when component mounts and data is ready
    if (studentData && calibrationData && !session) {
      initializeExam();
    }
  }, [studentData, calibrationData]);

  useEffect(() => {
    // Timer for exam duration
    if (isMonitoring) {
      const timer = setInterval(() => {
        setExamTime(prev => prev + 1);
      }, 1000);
      return () => clearInterval(timer);
    }
  }, [isMonitoring]);

  useEffect(() => {
    // Browser event monitoring: Copy/Paste and Tab Switching
    if (!session) return;

    const handleCopyPaste = async (e: KeyboardEvent) => {
      // Detect Ctrl+C, Ctrl+V, Cmd+C, Cmd+V
      if ((e.ctrlKey || e.metaKey) && (e.key === 'c' || e.key === 'v')) {
        const action = e.key === 'c' ? 'Copy' : 'Paste';
        toast.warning(`${action} attempt detected!`, { duration: 3000 });
        
        try {
          await api.reportBrowserViolation(
            session.id,
            'copy_paste',
            `Student attempted to ${action.toLowerCase()} content`
          );
          setViolationCount(prev => prev + 1);
          setWarnings(prev => [{
            type: 'copy_paste',
            message: `${action} attempt detected`,
            time: new Date().toLocaleTimeString()
          }, ...prev].slice(0, 10));
        } catch (error) {
          console.error('Failed to report copy/paste violation:', error);
        }
      }
    };

    const handleVisibilityChange = async () => {
      if (document.hidden) {
        toast.error('Tab switching detected! This is a violation.', { duration: 5000 });
        
        try {
          await api.reportBrowserViolation(
            session.id,
            'tab_switch',
            'Student switched tabs or minimized browser'
          );
          setViolationCount(prev => prev + 1);
          setWarnings(prev => [{
            type: 'tab_switch',
            message: 'Tab switching detected',
            time: new Date().toLocaleTimeString()
          }, ...prev].slice(0, 10));
        } catch (error) {
          console.error('Failed to report tab switch violation:', error);
        }
      }
    };

    const handleContextMenu = (e: MouseEvent) => {
      e.preventDefault();
      toast.warning('Right-click is disabled during exam', { duration: 2000 });
    };

    // Add event listeners
    document.addEventListener('keydown', handleCopyPaste);
    document.addEventListener('visibilitychange', handleVisibilityChange);
    document.addEventListener('contextmenu', handleContextMenu);

    // Cleanup
    return () => {
      document.removeEventListener('keydown', handleCopyPaste);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      document.removeEventListener('contextmenu', handleContextMenu);
    };
  }, [session]);



  useEffect(() => {
    // Audio/Noise Monitoring
    if (!session || !stream) return;

    let audioContext: AudioContext | null = null;
    let analyser: AnalyserNode | null = null;
    let microphone: MediaStreamAudioSourceNode | null = null;
    let monitoringInterval: NodeJS.Timeout | null = null;

    const setupAudioMonitoring = async () => {
      try {
        audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
        analyser = audioContext.createAnalyser();
        analyser.fftSize = 256;
        
        const audioTracks = stream.getAudioTracks();
        if (audioTracks.length > 0) {
          const audioStream = new MediaStream([audioTracks[0]]);
          microphone = audioContext.createMediaStreamSource(audioStream);
          microphone.connect(analyser);

          const bufferLength = analyser.frequencyBinCount;
          const dataArray = new Uint8Array(bufferLength);

          // Check audio level every 3 seconds
          monitoringInterval = setInterval(() => {
            if (!analyser) return;
            
            analyser.getByteFrequencyData(dataArray);
            const average = dataArray.reduce((a, b) => a + b) / bufferLength;
            
            // Threshold for excessive noise (adjusted for better sensitivity)
            const NOISE_THRESHOLD = 50; // 0-255 scale (lowered from 100 for better detection)
            
            console.log(`Audio level: ${Math.round(average)}`); // Debug logging
            
            if (average > NOISE_THRESHOLD) {
              toast.warning('Excessive noise detected!', { duration: 3000 });
              
              api.reportBrowserViolation(
                session.id,
                'excessive_noise',
                `Excessive noise detected (level: ${Math.round(average)})`
              ).then(() => {
                setViolationCount(prev => prev + 1);
                setWarnings(prev => [{
                  type: 'excessive_noise',
                  message: 'Excessive noise detected',
                  time: new Date().toLocaleTimeString()
                }, ...prev].slice(0, 10));
              }).catch(error => {
                console.error('Failed to report noise violation:', error);
              });
            }
          }, 3000);
        }
      } catch (error) {
        console.error('Audio monitoring setup error:', error);
      }
    };

    setupAudioMonitoring();

    return () => {
      if (monitoringInterval) clearInterval(monitoringInterval);
      if (microphone) microphone.disconnect();
      if (audioContext) audioContext.close();
    };
  }, [session, stream]);


  const initializeExam = async () => {
    try {
      if (!videoRef.current) return;

      // Start webcam
      const mediaStream = await startWebcam(videoRef.current);
      setStream(mediaStream);

      // Create exam session
      const newSession = await api.startSession(
        studentData.student_id,
        studentData.name,
        calibrationData.pitch,
        calibrationData.yaw
      );
      setSession(newSession);

      // Connect WebSocket for real-time updates
      connectWebSocket(newSession.id);

      // Start monitoring after a brief delay
      setTimeout(() => {
        startMonitoring(newSession);
      }, 2000);

      toast.success("Exam session started. AI monitoring is active.");
    } catch (error: any) {
      console.error('Exam initialization error:', error);
      toast.error(error.message || "Failed to start exam");
    }
  };

  const connectWebSocket = (sessionId: string) => {
    try {
      const ws = createWebSocket(`/ws/student/${sessionId}`);
      
      ws.onopen = () => {
        console.log('WebSocket connected');
      };

      ws.onmessage = (event) => {
        const message = JSON.parse(event.data);
        if (message.type === 'violation_warning') {
          toast.warning(message.data.message, { duration: 5000 });
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
      };

      ws.onclose = () => {
        console.log('WebSocket disconnected');
      };

      wsRef.current = ws;
    } catch (error) {
      console.error('WebSocket connection error:', error);
    }
  };

  const startMonitoring = (examSession: ExamSession) => {
    setIsMonitoring(true);

    // Process frame every 2 seconds
    monitoringInterval.current = setInterval(async () => {
      if (!videoRef.current || !examSession) return;

      try {
        const frameBase64 = captureFrame(videoRef.current);
        
        const result = await api.processFrame(
          examSession.id,
          frameBase64,
          calibrationData.pitch,
          calibrationData.yaw
        );

        // Update current violations
        const activeViolations: string[] = [];
        if (result.no_person) activeViolations.push('No Person');
        if (result.looking_away) activeViolations.push('Looking Away');
        if (result.multiple_faces) activeViolations.push('Multiple People');
        if (result.phone_detected) activeViolations.push('Phone Detected');
        if (result.book_detected) activeViolations.push('Book Detected');

        setCurrentViolations(activeViolations);

        // If new violations detected, add to warnings
        if (result.violations.length > 0) {
          const newWarnings = result.violations.map(v => ({
            type: v.type,
            message: v.message,
            time: new Date().toLocaleTimeString()
          }));
          
          setWarnings(prev => [...newWarnings, ...prev].slice(0, 10)); // Keep last 10
          setViolationCount(prev => prev + result.violations.length);

          // Show toast for high severity violations
          result.violations.forEach(v => {
            if (v.severity === 'high') {
              toast.error(v.message, { duration: 4000 });
            }
          });
        }

      } catch (error) {
        console.error('Frame processing error:', error);
      }
    }, 2000); // Process every 2 seconds
  };

  const stopMonitoring = () => {
    if (monitoringInterval.current) {
      clearInterval(monitoringInterval.current);
      monitoringInterval.current = null;
    }
    setIsMonitoring(false);
  };

  const endExam = async () => {
    if (!session) return;

    try {
      stopMonitoring();
      await api.endSession(session.id);
      cleanup();
      
      toast.success("Exam ended successfully!");
      navigate('/');
    } catch (error: any) {
      console.error('End exam error:', error);
      toast.error("Failed to end exam properly");
    }
  };

  const cleanup = () => {
    stopMonitoring();
    if (stream) {
      stopWebcam(stream);
    }
    if (wsRef.current) {
      wsRef.current.close();
    }
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const getViolationIcon = (type: string) => {
    switch (type) {
      case 'Looking Away':
        return <Eye className="w-4 h-4" />;
      case 'Multiple People':
        return <User2 className="w-4 h-4" />;
      case 'Phone Detected':
        return <Smartphone className="w-4 h-4" />;
      case 'Book Detected':
        return <Book className="w-4 h-4" />;
      default:
        return <AlertTriangle className="w-4 h-4" />;
    }
  };

  return (
    <div className="min-h-screen bg-background p-4">
      <div className="container mx-auto max-w-7xl">
        {/* Header */}
        <div className="mb-6 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-primary flex items-center justify-center">
              <Shield className="w-7 h-7 text-primary-foreground" />
            </div>
            <div>
              <h1 className="text-xl font-bold">Proctored Exam</h1>
              <p className="text-sm text-muted-foreground">
                {studentData?.name} ({studentData?.student_id})
              </p>
            </div>
          </div>

          <div className="flex items-center gap-4">
            {/* Timer */}
            <Card>
              <CardContent className="p-3 flex items-center gap-2">
                <Clock className="w-4 h-4" />
                <span className="font-mono font-semibold">{formatTime(examTime)}</span>
              </CardContent>
            </Card>

            {/* End Exam Button */}
            <Button onClick={endExam} variant="destructive">
              <LogOut className="w-4 h-4 mr-2" />
              End Exam
            </Button>
          </div>
        </div>

        <div className="grid lg:grid-cols-3 gap-6">
          {/* Main Content - Exam Area */}
          <div className="lg:col-span-2 space-y-6">
            {/* Exam Paper Card */}
            <Card>
              <CardContent className="p-8">
                <h2 className="text-2xl font-bold mb-6">Examination Paper</h2>
                <div className="space-y-6">
                  <div>
                    <h3 className="font-semibold text-lg mb-3">Question 1:</h3>
                    <p className="text-muted-foreground mb-4">
                      Explain the concept of artificial intelligence and its applications in modern proctoring systems.
                    </p>
                    <textarea
                      className="w-full min-h-[120px] p-3 border rounded-md"
                      placeholder="Type your answer here..."
                    />
                  </div>

                  <div>
                    <h3 className="font-semibold text-lg mb-3">Question 2:</h3>
                    <p className="text-muted-foreground mb-4">
                      Describe how computer vision techniques can be used for real-time monitoring.
                    </p>
                    <textarea
                      className="w-full min-h-[120px] p-3 border rounded-md"
                      placeholder="Type your answer here..."
                    />
                  </div>

                  <div>
                    <h3 className="font-semibold text-lg mb-3">Question 3:</h3>
                    <p className="text-muted-foreground mb-4">
                      What are the ethical considerations in AI-powered proctoring systems?
                    </p>
                    <textarea
                      className="w-full min-h-[120px] p-3 border rounded-md"
                      placeholder="Type your answer here..."
                    />
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Sidebar - Monitoring Info */}
          <div className="space-y-6">
            {/* Webcam Preview */}
            <Card>
              <CardContent className="p-4">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-semibold flex items-center gap-2">
                    <Camera className="w-4 h-4" />
                    Live Monitoring
                  </h3>
                  {isMonitoring && (
                    <Badge variant="destructive" className="animate-pulse">
                      LIVE
                    </Badge>
                  )}
                </div>
                <div className="aspect-video bg-black rounded-lg overflow-hidden">
                  <video
                    ref={videoRef}
                    autoPlay
                    playsInline
                    muted
                    className="w-full h-full object-cover"
                  />
                </div>
              </CardContent>
            </Card>

            {/* Current Violations */}
            <Card>
              <CardContent className="p-4">
                <h3 className="font-semibold mb-3 flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4" />
                  Active Alerts
                </h3>
                {currentViolations.length > 0 ? (
                  <div className="space-y-2">
                    {currentViolations.map((violation, idx) => (
                      <div key={idx} className="flex items-center gap-2 text-sm p-2 bg-destructive/10 rounded">
                        {getViolationIcon(violation)}
                        <span className="text-destructive font-medium">{violation}</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">No violations detected</p>
                )}
              </CardContent>
            </Card>

            {/* Violation Counter */}
            <Card>
              <CardContent className="p-4">
                <div className="text-center">
                  <div className="text-3xl font-bold text-destructive mb-1">
                    {violationCount}
                  </div>
                  <div className="text-sm text-muted-foreground">
                    Total Violations
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Recent Warnings */}
            <Card>
              <CardContent className="p-4">
                <h3 className="font-semibold mb-3">Recent Warnings</h3>
                <div className="space-y-2 max-h-48 overflow-y-auto">
                  {warnings.length > 0 ? (
                    warnings.map((warning, idx) => (
                      <div key={idx} className="text-xs p-2 bg-muted rounded">
                        <div className="flex items-center justify-between mb-1">
                          <Badge variant="outline" className="text-xs">{warning.type}</Badge>
                          <span className="text-muted-foreground">{warning.time}</span>
                        </div>
                        <p className="text-muted-foreground">{warning.message}</p>
                      </div>
                    ))
                  ) : (
                    <p className="text-xs text-muted-foreground">No warnings yet</p>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
};

export default StudentExam;
