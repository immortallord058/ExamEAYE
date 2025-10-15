import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { 
  Shield, Users, AlertTriangle, CheckCircle, Activity, Eye, 
  Smartphone, User2, Clock, LogOut, Download, RefreshCw, TrendingUp, BarChart3
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { toast } from "sonner";
import { api, ExamSession, Violation, createWebSocket } from "@/services/api";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

interface ViolationAlert {
  session_id: string;
  student_id: string;
  student_name: string;
  violation_type: string;
  severity: string;
  message: string;
  timestamp: string;
  snapshot_url?: string;
}

const AdminDashboard = () => {
  const navigate = useNavigate();
  const [stats, setStats] = useState({
    total_sessions: 0,
    active_sessions: 0,
    completed_sessions: 0,
    total_violations: 0
  });
  const [activeSessions, setActiveSessions] = useState<ExamSession[]>([]);
  const [studentsWithViolations, setStudentsWithViolations] = useState<any[]>([]);
  const [recentViolations, setRecentViolations] = useState<Violation[]>([]);
  const [liveAlerts, setLiveAlerts] = useState<ViolationAlert[]>([]);
  const [selectedSession, setSelectedSession] = useState<string | null>(null);
  const [sessionViolations, setSessionViolations] = useState<Violation[]>([]);
  const [loading, setLoading] = useState(true);
  const [averageStats, setAverageStats] = useState<any>(null);
  const [violationsTimeline, setViolationsTimeline] = useState<any[]>([]);
  
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    // Check admin authentication
    const isAdmin = sessionStorage.getItem('adminAuth');
    if (!isAdmin) {
      toast.error("Please login first");
      navigate('/admin/login');
      return;
    }

    // Initial data load
    loadDashboardData();

    // Connect to WebSocket for real-time updates
    connectWebSocket();

    // Refresh data every 5 seconds for real-time updates
    const interval = setInterval(loadDashboardData, 5000);

    return () => {
      clearInterval(interval);
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [navigate]);

  const connectWebSocket = () => {
    try {
      const ws = createWebSocket('/ws/admin');
      
      ws.onopen = () => {
        console.log('Admin WebSocket connected');
        toast.success("Connected to live monitoring");
      };

      ws.onmessage = (event) => {
        const message = JSON.parse(event.data);
        
        if (message.type === 'violation_alert') {
          // Add to live alerts
          const alert: ViolationAlert = message.data;
          setLiveAlerts(prev => [alert, ...prev].slice(0, 20)); // Keep last 20
          
          // Show toast notification
          toast.error(`${alert.student_name}: ${alert.message}`, {
            duration: 5000,
          });

          // Play alert sound
          playAlertSound();

          // Refresh recent violations
          loadRecentViolations();
        } else if (message.type === 'session_update') {
          // Refresh active sessions
          loadActiveSessions();
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
      };

      ws.onclose = () => {
        console.log('WebSocket disconnected');
        // Attempt reconnection after 5 seconds
        setTimeout(connectWebSocket, 5000);
      };

      wsRef.current = ws;
    } catch (error) {
      console.error('WebSocket connection error:', error);
    }
  };

  const playAlertSound = () => {
    // Play a simple beep sound
    const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
    const oscillator = audioContext.createOscillator();
    const gainNode = audioContext.createGain();
    
    oscillator.connect(gainNode);
    gainNode.connect(audioContext.destination);
    
    oscillator.frequency.value = 800;
    oscillator.type = 'sine';
    gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
    
    oscillator.start(audioContext.currentTime);
    oscillator.stop(audioContext.currentTime + 0.1);
  };

  const loadDashboardData = async () => {
    try {
      // First check backend connectivity
      console.log('🔗 Checking backend connectivity...');
      const healthCheck = await api.healthCheck();
      console.log('✅ Backend connected:', healthCheck);

      console.log('📊 Loading dashboard data...');
      const [statsData, sessionsData, studentsData, violationsData, avgStatsData, timelineData] = await Promise.all([
        api.getAdminStats().catch(err => {
          console.error('Stats error:', err);
          return { total_sessions: 0, active_sessions: 0, completed_sessions: 0, total_violations: 0 };
        }),
        api.getActiveSessions().catch(err => {
          console.error('Sessions error:', err);
          return [];
        }),
        api.getStudentsWithViolations().catch(err => {
          console.error('Students error:', err);
          return { students: [] };
        }),
        api.getRecentViolations(50).catch(err => {
          console.error('Violations error:', err);
          return [];
        }),
        api.getAverageStatistics().catch(err => {
          console.error('Avg stats error:', err);
          return null;
        }),
        api.getViolationsTimeline(100).catch(err => {
          console.error('Timeline error:', err);
          return { timeline: [] };
        })
      ]);

      console.log('✅ Data loaded successfully');
      setStats(statsData);
      setActiveSessions(sessionsData);
      setStudentsWithViolations(studentsData.students || []);
      setRecentViolations(violationsData);
      setAverageStats(avgStatsData);
      setViolationsTimeline(timelineData.timeline || []);
      setLoading(false);
      toast.success("Dashboard data loaded");
    } catch (error: any) {
      console.error('❌ Error loading dashboard data:', error);
      toast.error("Failed to load dashboard data: " + (error.message || "Connection error"));
      setLoading(false);
    }
  };

  const loadActiveSessions = async () => {
    try {
      const sessions = await api.getActiveSessions();
      setActiveSessions(sessions);
    } catch (error) {
      console.error('Error loading active sessions:', error);
    }
  };

  const loadRecentViolations = async () => {
    try {
      const violations = await api.getRecentViolations(50);
      setRecentViolations(violations);
    } catch (error) {
      console.error('Error loading violations:', error);
    }
  };

  const handleViewSession = async (sessionId: string) => {
    setSelectedSession(sessionId);
    try {
      const violations = await api.getSessionViolations(sessionId);
      setSessionViolations(violations);
    } catch (error) {
      console.error('Error loading session violations:', error);
      toast.error("Failed to load session details");
    }
  };

  const handleLogout = () => {
    sessionStorage.removeItem('adminAuth');
    if (wsRef.current) {
      wsRef.current.close();
    }
    navigate('/admin/login');
  };

  const getViolationIcon = (type: string) => {
    switch (type) {
      case 'looking_away':
        return <Eye className="w-4 h-4" />;
      case 'multiple_faces':
        return <User2 className="w-4 h-4" />;
      case 'no_person':
        return <User2 className="w-4 h-4" />;
      case 'phone_detected':
        return <Smartphone className="w-4 h-4" />;
      case 'book_detected':
        return <AlertTriangle className="w-4 h-4" />;
      case 'copy_paste':
        return <AlertTriangle className="w-4 h-4" />;
      case 'tab_switch':
        return <AlertTriangle className="w-4 h-4" />;
      case 'excessive_noise':
        return <Activity className="w-4 h-4" />;
      default:
        return <AlertTriangle className="w-4 h-4" />;
    }
  };

  const getViolationLabel = (type: string) => {
    const labels: Record<string, string> = {
      'looking_away': 'Looking Away',
      'multiple_faces': 'Multiple People',
      'no_person': 'No Person',
      'phone_detected': 'Phone Detected',
      'book_detected': 'Book Detected',
      'copy_paste': 'Copy/Paste Attempt',
      'tab_switch': 'Tab Switching',
      'excessive_noise': 'Excessive Noise'
    };
    return labels[type] || type.replace('_', ' ');
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'high':
        return 'bg-red-500';
      case 'medium':
        return 'bg-yellow-500';
      case 'low':
        return 'bg-blue-500';
      default:
        return 'bg-gray-500';
    }
  };

  const formatTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString();
  };

  const formatDuration = (startTime: string) => {
    const start = new Date(startTime);
    const now = new Date();
    const diff = Math.floor((now.getTime() - start.getTime()) / 1000 / 60); // minutes
    return `${diff} min`;
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <RefreshCw className="w-8 h-8 animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background p-6">
      <div className="container mx-auto max-w-7xl">
        {/* Header */}
        <div className="mb-8 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-primary flex items-center justify-center">
              <Shield className="w-7 h-7 text-primary-foreground" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-foreground">Admin Dashboard</h1>
              <p className="text-sm text-gray-600 dark:text-gray-400">Real-time Exam Monitoring</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <Button variant="outline" onClick={loadDashboardData}>
              <RefreshCw className="w-4 h-4 mr-2" />
              Refresh
            </Button>
            <Button 
              variant="outline" 
              onClick={() => window.open(api.exportSummaryCSV(), '_blank')}
            >
              <Download className="w-4 h-4 mr-2" />
              Export CSV
            </Button>
            <Button 
              variant="outline" 
              onClick={() => window.open(api.exportReportHTML(), '_blank')}
            >
              <Download className="w-4 h-4 mr-2" />
              Export Report
            </Button>
            <Button variant="outline" onClick={handleLogout}>
              <LogOut className="w-4 h-4 mr-2" />
              Logout
            </Button>
          </div>
        </div>

        {/* Stats Cards */}
        <div className="grid md:grid-cols-4 gap-6 mb-6">
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600 dark:text-gray-400 mb-1 font-medium">Total Sessions</p>
                  <p className="text-3xl font-bold text-foreground">{stats.total_sessions}</p>
                </div>
                <Activity className="w-8 h-8 text-blue-500" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600 dark:text-gray-400 mb-1 font-medium">Active Now</p>
                  <p className="text-3xl font-bold text-green-600 dark:text-green-500">{stats.active_sessions}</p>
                </div>
                <Users className="w-8 h-8 text-green-500" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600 dark:text-gray-400 mb-1 font-medium">Completed</p>
                  <p className="text-3xl font-bold text-foreground">{stats.completed_sessions}</p>
                </div>
                <CheckCircle className="w-8 h-8 text-blue-500" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600 dark:text-gray-400 mb-1 font-medium">Total Violations</p>
                  <p className="text-3xl font-bold text-red-600 dark:text-red-500">{stats.total_violations}</p>
                </div>
                <AlertTriangle className="w-8 h-8 text-red-500" />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Average Statistics Cards */}
        {averageStats && (
          <div className="grid md:grid-cols-3 gap-6 mb-6">
            <Card>
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-600 dark:text-gray-400 mb-1 font-medium">Avg Violations/Student</p>
                    <p className="text-3xl font-bold text-foreground">{averageStats.avg_violations_per_student}</p>
                  </div>
                  <TrendingUp className="w-8 h-8 text-orange-500" />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-600 dark:text-gray-400 mb-1 font-medium">Avg Exam Duration</p>
                    <p className="text-3xl font-bold text-foreground">{averageStats.avg_exam_duration_minutes.toFixed(0)} min</p>
                  </div>
                  <Clock className="w-8 h-8 text-purple-500" />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-600 dark:text-gray-400 mb-1 font-medium">Total Students</p>
                    <p className="text-3xl font-bold text-foreground">{averageStats.total_students}</p>
                  </div>
                  <Users className="w-8 h-8 text-cyan-500" />
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Violations Timeline Chart */}
        {violationsTimeline.length > 0 && (
          <Card className="mb-6">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <BarChart3 className="w-5 h-5" />
                Violations Over Time
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-[300px]">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={violationsTimeline}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis 
                      dataKey="timestamp" 
                      tickFormatter={(value) => new Date(value).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    />
                    <YAxis />
                    <Tooltip 
                      labelFormatter={(value) => new Date(value).toLocaleString()}
                      formatter={(value) => [`${value} violations`, 'Count']}
                    />
                    <Line 
                      type="monotone" 
                      dataKey="count" 
                      stroke="#ef4444" 
                      strokeWidth={2}
                      dot={{ fill: '#ef4444', r: 4 }}
                      activeDot={{ r: 6 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>
        )}


        {/* Evidence Gallery Section */}
        {recentViolations.filter(v => v.snapshot_url || v.snapshot_base64).length > 0 && (
          <Card className="mb-6">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Eye className="w-5 h-5" />
                Recent Violation Evidence Gallery
                <Badge variant="secondary" className="ml-2">
                  {recentViolations.filter(v => v.snapshot_url || v.snapshot_base64).length} Images
                </Badge>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                {recentViolations
                  .filter(v => v.snapshot_url || v.snapshot_base64)
                  .slice(0, 12)
                  .map((violation) => {
                    const imageUrl = violation.snapshot_url || 
                      (violation.snapshot_base64?.startsWith('data:') 
                        ? violation.snapshot_base64 
                        : `data:image/jpeg;base64,${violation.snapshot_base64}`);
                    
                    const handleDownload = () => {
                      const link = document.createElement('a');
                      link.href = imageUrl;
                      link.download = `violation_${violation.student_name}_${violation.violation_type}_${new Date(violation.timestamp).getTime()}.jpg`;
                      document.body.appendChild(link);
                      link.click();
                      document.body.removeChild(link);
                    };
                    
                    return (
                    <div 
                      key={violation.id} 
                      className="relative group cursor-pointer"
                      onClick={handleDownload}
                    >
                      <div className="relative overflow-hidden rounded-lg border-2 border-gray-200 dark:border-gray-700 hover:border-primary transition-all">
                        <img 
                          src={imageUrl} 
                          alt={`${violation.violation_type} evidence`}
                          className="w-full h-40 object-cover group-hover:scale-110 transition-transform duration-300"
                        />
                        <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/40 to-transparent">
                          <div className="absolute bottom-0 left-0 right-0 p-2 text-white">
                            <p className="text-xs font-bold truncate">{violation.student_name}</p>
                            <p className="text-xs">
                              <Badge variant="destructive" className="text-xs">
                                {getViolationLabel(violation.violation_type)}
                              </Badge>
                            </p>
                            <p className="text-xs opacity-90 mt-1">
                              {new Date(violation.timestamp).toLocaleString()}
                            </p>
                          </div>
                        </div>
                        {/* Hover overlay */}
                        <div className="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-all flex flex-col items-center justify-center">
                          <Download className="w-8 h-8 text-white opacity-0 group-hover:opacity-100 transition-all" />
                          <span className="text-white text-xs mt-2 opacity-0 group-hover:opacity-100 transition-all font-semibold">Click to Download</span>
                        </div>
                      </div>
                    </div>
                  );
                  })}
              </div>
            </CardContent>
          </Card>
        )}


        <div className="grid lg:grid-cols-3 gap-6">
          {/* Students with Violations */}
          <div className="lg:col-span-2 space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Users className="w-5 h-5" />
                  Students with Violations
                  {studentsWithViolations.length > 0 && (
                    <Badge variant="destructive" className="ml-2">
                      {studentsWithViolations.length} Students
                    </Badge>
                  )}
                </CardTitle>
              </CardHeader>
              <CardContent>
                {studentsWithViolations.length > 0 ? (
                  <div className="space-y-3">
                    {studentsWithViolations.map((student) => (
                      <Card key={student.student_id} className="border-2 hover:border-primary transition-all">
                        <CardContent className="p-4">
                          <div className="flex items-start gap-4">
                            {/* Student Image */}
                            <div className="flex-shrink-0">
                              {student.latest_snapshot && (
                                <img 
                                  src={
                                    student.latest_snapshot.startsWith('http') 
                                      ? student.latest_snapshot 
                                      : student.latest_snapshot.startsWith('data:')
                                        ? student.latest_snapshot
                                        : `data:image/jpeg;base64,${student.latest_snapshot}`
                                  }
                                  alt={student.student_name}
                                  className="w-24 h-24 object-cover rounded-lg border-2 border-red-300"
                                />
                              )}
                            </div>
                            
                            {/* Student Info */}
                            <div className="flex-1">
                              <div className="flex items-center gap-3 mb-2">
                                <h4 className="font-bold text-foreground text-lg">{student.student_name}</h4>
                                <Badge variant="outline" className="font-medium">{student.student_id}</Badge>
                              </div>
                              <div className="flex items-center gap-4 text-sm text-gray-600 dark:text-gray-400 mb-2">
                                <span className="flex items-center gap-1 font-medium">
                                  <AlertTriangle className="w-4 h-4 text-red-500" />
                                  <span className="text-red-600 dark:text-red-400 font-bold">{student.violation_count}</span> Violations
                                </span>
                              </div>
                              <div className="flex flex-wrap gap-1 mb-3">
                                {student.violation_types.map((type: string) => (
                                  <Badge key={type} variant="secondary" className="text-xs">
                                    {getViolationLabel(type)}
                                  </Badge>
                                ))}
                              </div>
                              
                              {/* Export Buttons */}
                              <div className="flex gap-2">
                                <Button
                                  size="sm"
                                  variant="outline"
                                  onClick={() => window.open(api.exportStudentViolationsCSV(student.student_id), '_blank')}
                                >
                                  <Download className="w-3 h-3 mr-1" />
                                  CSV
                                </Button>
                                <Button
                                  size="sm"
                                  variant="outline"
                                  onClick={() => window.open(api.exportStudentReportHTML(student.student_id), '_blank')}
                                >
                                  <Download className="w-3 h-3 mr-1" />
                                  Report
                                </Button>
                              </div>
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                ) : (
                  <p className="text-center text-gray-600 dark:text-gray-400 py-8 font-medium">
                    No students with violations
                  </p>
                )}
              </CardContent>
            </Card>

            {/* Recent Violations */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <AlertTriangle className="w-5 h-5" />
                  Recent Violations
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ScrollArea className="h-[400px]">
                  {recentViolations.length > 0 ? (
                    <div className="space-y-3">
                      {recentViolations.map((violation) => (
                        <Card key={violation.id} className="border">
                          <CardContent className="p-4">
                            <div className="flex items-start gap-3">
                              <div className={`w-8 h-8 rounded-full flex items-center justify-center ${getSeverityColor(violation.severity)}`}>
                                {getViolationIcon(violation.violation_type)}
                              </div>
                              <div className="flex-1">
                                <div className="flex items-center gap-2 mb-1">
                                  <span className="font-semibold text-foreground">{violation.student_name}</span>
                                  <Badge variant="outline" className="text-xs font-medium">
                                    {getViolationLabel(violation.violation_type)}
                                  </Badge>
                                </div>
                                <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
                                  {violation.message}
                                </p>
                                <div className="flex items-center justify-between">
                                  <span className="text-xs text-gray-500 dark:text-gray-400 font-medium">
                                    {formatTime(violation.timestamp)}
                                  </span>
                                  {violation.snapshot_url && (
                                    <Button
                                      size="sm"
                                      variant="link"
                                      onClick={() => window.open(violation.snapshot_url, '_blank')}
                                    >
                                      View Snapshot
                                    </Button>
                                  )}
                                </div>
                              </div>
                            </div>
                            {(violation.snapshot_url || violation.snapshot_base64) && (
                              <div className="mt-3 relative group">
                                <img 
                                  src={
                                    violation.snapshot_url || 
                                    (violation.snapshot_base64?.startsWith('data:') 
                                      ? violation.snapshot_base64 
                                      : `data:image/jpeg;base64,${violation.snapshot_base64}`)
                                  }
                                  alt="Violation snapshot"
                                  className="w-full h-48 object-cover rounded-lg border-2 border-red-200 dark:border-red-800 cursor-pointer hover:border-red-500 transition-all"
                                  onClick={() => {
                                    const imageUrl = violation.snapshot_url || 
                                      (violation.snapshot_base64?.startsWith('data:') 
                                        ? violation.snapshot_base64 
                                        : `data:image/jpeg;base64,${violation.snapshot_base64}`);
                                    window.open(imageUrl, '_blank');
                                  }}
                                />
                                <div className="absolute top-2 left-2 bg-black/80 text-white px-3 py-1.5 rounded-md text-xs font-semibold shadow-lg">
                                  {getViolationLabel(violation.violation_type)} - {new Date(violation.timestamp).toLocaleString()}
                                </div>
                                <div className="absolute inset-0 bg-black/0 group-hover:bg-black/10 transition-all rounded-lg flex items-center justify-center">
                                  <Eye className="w-8 h-8 text-white opacity-0 group-hover:opacity-100 transition-all" />
                                </div>
                              </div>
                            )}
                          </CardContent>
                        </Card>
                      ))}
                    </div>
                  ) : (
                    <p className="text-center text-gray-600 dark:text-gray-400 py-8 font-medium">
                      No violations recorded
                    </p>
                  )}
                </ScrollArea>
              </CardContent>
            </Card>
          </div>

          {/* Live Alerts Feed */}
          <div>
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Activity className="w-5 h-5" />
                  Live Alerts
                  <Badge variant="destructive" className="ml-auto animate-pulse">
                    LIVE
                  </Badge>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ScrollArea className="h-[600px]">
                  {liveAlerts.length > 0 ? (
                    <div className="space-y-3">
                      {liveAlerts.map((alert, idx) => (
                        <div 
                          key={idx}
                          className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg animate-in fade-in slide-in-from-top duration-300"
                        >
                          <div className="flex items-start gap-2">
                            <div className="w-6 h-6 rounded-full bg-red-500 flex items-center justify-center flex-shrink-0">
                              {getViolationIcon(alert.violation_type)}
                            </div>
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2 mb-1">
                                <span className="font-semibold text-sm truncate text-foreground">
                                  {alert.student_name}
                                </span>
                                <Badge variant="destructive" className="text-xs font-medium">
                                  {alert.severity}
                                </Badge>
                              </div>
                              <p className="text-xs text-gray-600 dark:text-gray-400 mb-1 font-medium">
                                {alert.message}
                              </p>
                              <p className="text-xs text-gray-500 dark:text-gray-400 font-medium">
                                {formatTime(alert.timestamp)}
                              </p>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-center text-gray-600 dark:text-gray-400 py-8">
                      <Activity className="w-12 h-12 mx-auto mb-3 opacity-50" />
                      <p className="font-medium">Monitoring for violations...</p>
                      <p className="text-xs mt-1 font-medium">Live alerts will appear here</p>
                    </div>
                  )}
                </ScrollArea>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AdminDashboard;
