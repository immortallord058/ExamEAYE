import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { Shield, Camera, Sun, User, CheckCircle2, AlertCircle, Loader2, ArrowRight, Mic } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { toast } from "sonner";
import { api } from "@/services/api";
import { startWebcam, stopWebcam, captureFrame } from "@/utils/webcam";

const StudentVerify = () => {
  const navigate = useNavigate();
  const [studentData, setStudentData] = useState<any>(null);
  const [currentStep, setCurrentStep] = useState(0);
  const [checks, setChecks] = useState({
    camera: { status: 'pending', message: 'Waiting...' },
    microphone: { status: 'pending', message: 'Waiting...' },
    lighting: { status: 'pending', message: 'Waiting...' },
    face: { status: 'pending', message: 'Waiting...' },
  });
  const [verifying, setVerifying] = useState(false);
  const [stream, setStream] = useState<MediaStream | null>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const [calibrationData, setCalibrationData] = useState<{ pitch: number; yaw: number } | null>(null);

  useEffect(() => {
    const data = sessionStorage.getItem('studentData');
    if (!data) {
      toast.error("Please register first");
      navigate('/student/register');
      return;
    }
    setStudentData(JSON.parse(data));

    return () => {
      if (stream) {
        stopWebcam(stream);
      }
    };
  }, [navigate]);

  const startVerification = async () => {
    if (!videoRef.current) return;
    
    setVerifying(true);
    
    try {
      // Step 1: Camera Access
      setCurrentStep(1);
      setChecks(prev => ({
        ...prev,
        camera: { status: 'checking', message: 'Requesting camera access...' }
      }));

      const mediaStream = await navigator.mediaDevices.getUserMedia({
        video: true,
        audio: true  // Request audio access
      });
      
      if (videoRef.current) {
        videoRef.current.srcObject = mediaStream;
      }
      setStream(mediaStream);

      setChecks(prev => ({
        ...prev,
        camera: { status: 'success', message: 'Camera access granted' }
      }));

      // Check microphone
      setChecks(prev => ({
        ...prev,
        microphone: { status: 'checking', message: 'Checking microphone...' }
      }));

      const audioTracks = mediaStream.getAudioTracks();
      if (audioTracks.length > 0 && audioTracks[0].enabled) {
        setChecks(prev => ({
          ...prev,
          microphone: { status: 'success', message: 'Microphone access granted' }
        }));
      } else {
        setChecks(prev => ({
          ...prev,
          microphone: { status: 'error', message: 'Microphone not found' }
        }));
      }

      // Wait for video to be ready
      await new Promise(resolve => setTimeout(resolve, 1000));

      // Step 2: Environment Check (Lighting + Face Detection)
      setCurrentStep(2);
      setChecks(prev => ({
        ...prev,
        lighting: { status: 'checking', message: 'Analyzing environment...' },
        face: { status: 'checking', message: 'Detecting face...' }
      }));

      const frameBase64 = captureFrame(videoRef.current);
      const envCheck = await api.checkEnvironment(frameBase64);

      if (envCheck.face_detected) {
        setChecks(prev => ({
          ...prev,
          lighting: { status: 'success', message: envCheck.lighting_ok ? 'Good lighting' : 'Lighting acceptable' },
          face: { status: 'success', message: 'Face detected and centered' }
        }));
      } else {
        setChecks(prev => ({
          ...prev,
          lighting: { status: 'warning', message: 'Poor lighting detected' },
          face: { status: 'error', message: 'No face detected. Please adjust camera.' }
        }));
        toast.error("Environment check failed. Please ensure good lighting and face the camera.");
        setVerifying(false);
        return;
      }

      // Step 3: Calibration
      setCurrentStep(3);
      toast.info("Please look straight at the camera for calibration...", { duration: 3000 });
      await new Promise(resolve => setTimeout(resolve, 2000));

      const calibrationFrames: { pitch: number; yaw: number }[] = [];
      
      // Capture multiple frames for calibration
      for (let i = 0; i < 5; i++) {
        const frame = captureFrame(videoRef.current);
        const calibResult = await api.calibrate(frame);
        
        if (calibResult.success && calibResult.pitch !== undefined && calibResult.yaw !== undefined) {
          calibrationFrames.push({ pitch: calibResult.pitch, yaw: calibResult.yaw });
        }
        
        await new Promise(resolve => setTimeout(resolve, 200));
      }

      if (calibrationFrames.length === 0) {
        toast.error("Calibration failed. Please try again.");
        setVerifying(false);
        return;
      }

      // Average calibration values
      const avgPitch = calibrationFrames.reduce((sum, f) => sum + f.pitch, 0) / calibrationFrames.length;
      const avgYaw = calibrationFrames.reduce((sum, f) => sum + f.yaw, 0) / calibrationFrames.length;
      
      setCalibrationData({ pitch: avgPitch, yaw: avgYaw });

      // All checks complete
      toast.success("Environment verification complete!");
      
      // Store calibration data
      sessionStorage.setItem('calibrationData', JSON.stringify({
        pitch: avgPitch,
        yaw: avgYaw
      }));

      setTimeout(() => {
        navigate('/student/exam');
      }, 1500);

    } catch (error: any) {
      console.error('Verification error:', error);
      toast.error(error.message || "Verification failed. Please try again.");
      setChecks(prev => ({
        ...prev,
        camera: { status: 'error', message: error.message }
      }));
      setVerifying(false);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'success':
        return <CheckCircle2 className="w-5 h-5 text-green-500" />;
      case 'checking':
        return <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />;
      case 'error':
        return <AlertCircle className="w-5 h-5 text-red-500" />;
      case 'warning':
        return <AlertCircle className="w-5 h-5 text-yellow-500" />;
      default:
        return <div className="w-5 h-5 rounded-full border-2 border-gray-300" />;
    }
  };

  const progress = (currentStep / 3) * 100;

  return (
    <div className="min-h-screen bg-background p-4">
      {/* Header */}
      <div className="container mx-auto max-w-5xl">
        <div className="mb-8 flex items-center gap-3">
          <div className="w-12 h-12 rounded-xl bg-primary flex items-center justify-center">
            <Shield className="w-7 h-7 text-primary-foreground" />
          </div>
          <div>
            <h1 className="text-xl font-bold">Environment Verification</h1>
            <p className="text-sm text-muted-foreground">
              {studentData?.name} ({studentData?.student_id})
            </p>
          </div>
        </div>

        <div className="grid lg:grid-cols-2 gap-6">
          {/* Webcam Preview */}
          <Card>
            <CardContent className="p-6">
              <h3 className="font-semibold mb-4">Camera Preview</h3>
              <div className="relative aspect-video bg-black rounded-lg overflow-hidden">
                <video
                  ref={videoRef}
                  autoPlay
                  playsInline
                  muted
                  className="w-full h-full object-cover"
                />
                {!stream && (
                  <div className="absolute inset-0 flex items-center justify-center text-white">
                    <Camera className="w-16 h-16 opacity-50" />
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Verification Checklist */}
          <div className="space-y-6">
            <Card>
              <CardContent className="p-6">
                <h3 className="font-semibold mb-4">Verification Progress</h3>
                <Progress value={progress} className="mb-6" />

                <div className="space-y-4">
                  {/* Camera Check */}
                  <div className="flex items-start gap-3">
                    {getStatusIcon(checks.camera.status)}
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <Camera className="w-4 h-4" />
                        <span className="font-medium">Camera Access</span>
                      </div>
                      <p className="text-sm text-muted-foreground">{checks.camera.message}</p>
                    </div>
                  </div>

                  {/* Microphone Check */}
                  <div className="flex items-start gap-3">
                    {getStatusIcon(checks.microphone.status)}
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <Mic className="w-4 h-4" />
                        <span className="font-medium">Microphone Access</span>
                      </div>
                      <p className="text-sm text-muted-foreground">{checks.microphone.message}</p>
                    </div>
                  </div>


                  {/* Lighting Check */}
                  <div className="flex items-start gap-3">
                    {getStatusIcon(checks.lighting.status)}
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <Sun className="w-4 h-4" />
                        <span className="font-medium">Lighting Conditions</span>
                      </div>
                      <p className="text-sm text-muted-foreground">{checks.lighting.message}</p>
                    </div>
                  </div>

                  {/* Face Detection Check */}
                  <div className="flex items-start gap-3">
                    {getStatusIcon(checks.face.status)}
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <User className="w-4 h-4" />
                        <span className="font-medium">Face Detection</span>
                      </div>
                      <p className="text-sm text-muted-foreground">{checks.face.message}</p>
                    </div>
                  </div>
                </div>

                <Button
                  onClick={startVerification}
                  disabled={verifying}
                  className="w-full mt-6"
                  size="lg"
                >
                  {verifying ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Verifying...
                    </>
                  ) : (
                    <>
                      Start Verification
                      <ArrowRight className="w-4 h-4 ml-2" />
                    </>
                  )}
                </Button>
              </CardContent>
            </Card>

            {/* Instructions */}
            <Card className="bg-muted/50">
              <CardContent className="p-6">
                <h4 className="font-semibold mb-3">Before you start:</h4>
                <ul className="space-y-2 text-sm text-muted-foreground">
                  <li className="flex items-start gap-2">
                    <div className="w-1.5 h-1.5 rounded-full bg-primary mt-1.5"></div>
                    Ensure you're in a well-lit room
                  </li>
                  <li className="flex items-start gap-2">
                    <div className="w-1.5 h-1.5 rounded-full bg-primary mt-1.5"></div>
                    Position yourself at the center of the camera
                  </li>
                  <li className="flex items-start gap-2">
                    <div className="w-1.5 h-1.5 rounded-full bg-primary mt-1.5"></div>
                    No other person should be visible
                  </li>
                  <li className="flex items-start gap-2">
                    <div className="w-1.5 h-1.5 rounded-full bg-primary mt-1.5"></div>
                    Remove any background noise
                  </li>
                </ul>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
};

export default StudentVerify;
