#!/usr/bin/env python3
"""
Backend API Testing for AI Proctoring System
Tests the specific endpoints mentioned in the review request
"""

import requests
import json
import sys
from datetime import datetime
from typing import Dict, Any, Optional

# Backend URL from environment
BACKEND_URL = "https://codeimporter.preview.emergentagent.com"
API_BASE = f"{BACKEND_URL}/api"

class APITester:
    def __init__(self):
        self.session = requests.Session()
        self.results = []
        
    def log_result(self, test_name: str, success: bool, details: str, response_data: Any = None):
        """Log test result"""
        result = {
            'test': test_name,
            'success': success,
            'details': details,
            'timestamp': datetime.now().isoformat(),
            'response_data': response_data
        }
        self.results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {details}")
        if response_data and not success:
            print(f"   Response: {response_data}")
        print()

    def test_health_check(self):
        """Test GET /api/health"""
        try:
            response = self.session.get(f"{API_BASE}/health", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                self.log_result(
                    "Health Check", 
                    True, 
                    f"Status: {response.status_code}, Response: {data}",
                    data
                )
                return True
            else:
                self.log_result(
                    "Health Check", 
                    False, 
                    f"Expected 200, got {response.status_code}",
                    response.text
                )
                return False
                
        except Exception as e:
            self.log_result("Health Check", False, f"Request failed: {str(e)}")
            return False

    def test_admin_stats(self):
        """Test GET /api/admin/stats"""
        try:
            response = self.session.get(f"{API_BASE}/admin/stats", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Validate expected fields
                required_fields = ['total_sessions', 'active_sessions', 'completed_sessions', 'total_violations']
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    self.log_result(
                        "Admin Stats", 
                        False, 
                        f"Missing required fields: {missing_fields}",
                        data
                    )
                    return False
                
                # Check if values are numeric
                numeric_check = all(isinstance(data[field], (int, float)) for field in required_fields)
                
                if numeric_check:
                    self.log_result(
                        "Admin Stats", 
                        True, 
                        f"All fields present with numeric values: {data}",
                        data
                    )
                    return True
                else:
                    self.log_result(
                        "Admin Stats", 
                        False, 
                        f"Non-numeric values found in stats",
                        data
                    )
                    return False
                    
            else:
                self.log_result(
                    "Admin Stats", 
                    False, 
                    f"Expected 200, got {response.status_code}",
                    response.text
                )
                return False
                
        except Exception as e:
            self.log_result("Admin Stats", False, f"Request failed: {str(e)}")
            return False

    def test_average_statistics(self):
        """Test GET /api/admin/statistics/average"""
        try:
            response = self.session.get(f"{API_BASE}/admin/statistics/average", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Validate expected fields
                required_fields = ['avg_violations_per_student', 'avg_exam_duration_minutes', 'total_students', 'total_sessions']
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    self.log_result(
                        "Average Statistics", 
                        False, 
                        f"Missing required fields: {missing_fields}",
                        data
                    )
                    return False
                
                # Check if values are numeric
                numeric_fields = ['avg_violations_per_student', 'avg_exam_duration_minutes', 'total_students', 'total_sessions']
                numeric_check = all(isinstance(data[field], (int, float)) for field in numeric_fields)
                
                if numeric_check:
                    self.log_result(
                        "Average Statistics", 
                        True, 
                        f"All fields present with proper values: {data}",
                        data
                    )
                    return True
                else:
                    self.log_result(
                        "Average Statistics", 
                        False, 
                        f"Non-numeric values found in statistics",
                        data
                    )
                    return False
                    
            else:
                self.log_result(
                    "Average Statistics", 
                    False, 
                    f"Expected 200, got {response.status_code}",
                    response.text
                )
                return False
                
        except Exception as e:
            self.log_result("Average Statistics", False, f"Request failed: {str(e)}")
            return False

    def test_violations_timeline(self):
        """Test GET /api/admin/violations/timeline?limit=50"""
        try:
            response = self.session.get(f"{API_BASE}/admin/violations/timeline?limit=50", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Should have timeline field
                if 'timeline' not in data:
                    self.log_result(
                        "Violations Timeline", 
                        False, 
                        "Missing 'timeline' field in response",
                        data
                    )
                    return False
                
                timeline = data['timeline']
                
                # Timeline should be an array
                if not isinstance(timeline, list):
                    self.log_result(
                        "Violations Timeline", 
                        False, 
                        "Timeline should be an array",
                        data
                    )
                    return False
                
                # If timeline has data, validate structure
                if timeline:
                    first_item = timeline[0]
                    if 'timestamp' not in first_item or 'count' not in first_item:
                        self.log_result(
                            "Violations Timeline", 
                            False, 
                            "Timeline items missing required fields (timestamp, count)",
                            data
                        )
                        return False
                
                self.log_result(
                    "Violations Timeline", 
                    True, 
                    f"Timeline returned with {len(timeline)} data points",
                    data
                )
                return True
                    
            else:
                self.log_result(
                    "Violations Timeline", 
                    False, 
                    f"Expected 200, got {response.status_code}",
                    response.text
                )
                return False
                
        except Exception as e:
            self.log_result("Violations Timeline", False, f"Request failed: {str(e)}")
            return False

    def get_active_sessions(self):
        """Get active sessions for browser violation testing"""
        try:
            response = self.session.get(f"{API_BASE}/sessions/active/list", timeout=10)
            
            if response.status_code == 200:
                sessions = response.json()
                self.log_result(
                    "Get Active Sessions", 
                    True, 
                    f"Found {len(sessions)} active sessions",
                    sessions
                )
                return sessions
            else:
                self.log_result(
                    "Get Active Sessions", 
                    False, 
                    f"Expected 200, got {response.status_code}",
                    response.text
                )
                return []
                
        except Exception as e:
            self.log_result("Get Active Sessions", False, f"Request failed: {str(e)}")
            return []

    def test_browser_violation(self, session_id: str):
        """Test POST /api/proctoring/browser-violation"""
        try:
            payload = {
                "session_id": session_id,
                "violation_type": "tab_switch",
                "message": "Test tab switch violation"
            }
            
            response = self.session.post(
                f"{API_BASE}/proctoring/browser-violation", 
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Should return success message and violation_id
                if 'message' in data and 'violation_id' in data:
                    self.log_result(
                        "Browser Violation", 
                        True, 
                        f"Violation recorded successfully: {data}",
                        data
                    )
                    return True
                else:
                    self.log_result(
                        "Browser Violation", 
                        False, 
                        "Missing expected fields in response",
                        data
                    )
                    return False
                    
            else:
                self.log_result(
                    "Browser Violation", 
                    False, 
                    f"Expected 200, got {response.status_code}",
                    response.text
                )
                return False
                
        except Exception as e:
            self.log_result("Browser Violation", False, f"Request failed: {str(e)}")
            return False

    def run_all_tests(self):
        """Run all API tests"""
        print("=" * 60)
        print("AI PROCTORING SYSTEM - BACKEND API TESTS")
        print("=" * 60)
        print(f"Testing Backend URL: {BACKEND_URL}")
        print(f"API Base: {API_BASE}")
        print("=" * 60)
        print()
        
        # Test 1: Health Check
        health_ok = self.test_health_check()
        
        # Test 2: Admin Stats
        stats_ok = self.test_admin_stats()
        
        # Test 3: Average Statistics
        avg_stats_ok = self.test_average_statistics()
        
        # Test 4: Violations Timeline
        timeline_ok = self.test_violations_timeline()
        
        # Test 5: Browser Violation (if active session exists)
        active_sessions = self.get_active_sessions()
        browser_violation_ok = True  # Default to true if no sessions to test
        
        if active_sessions:
            session_id = active_sessions[0]['id']
            browser_violation_ok = self.test_browser_violation(session_id)
        else:
            self.log_result(
                "Browser Violation", 
                True, 
                "No active sessions found - skipping browser violation test (this is expected)",
                None
            )
        
        # Summary
        print("=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r['success'])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print()
        
        if failed_tests > 0:
            print("FAILED TESTS:")
            for result in self.results:
                if not result['success']:
                    print(f"  ❌ {result['test']}: {result['details']}")
            print()
        
        print("DETAILED RESULTS:")
        for result in self.results:
            status = "✅" if result['success'] else "❌"
            print(f"  {status} {result['test']}")
        
        print("=" * 60)
        
        # Return overall success
        return failed_tests == 0

if __name__ == "__main__":
    tester = APITester()
    success = tester.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)