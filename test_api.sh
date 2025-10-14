#!/bin/bash

# Test script for ExamEye Shield API endpoints

BASE_URL="https://codeimporter.preview.emergentagent.com/api"

echo "🧪 Testing ExamEye Shield API Endpoints"
echo "========================================"
echo ""

# Test 1: Health check
echo "1. Testing Health Check..."
curl -s "$BASE_URL/health" | jq '.status' && echo "✅ Health check passed" || echo "❌ Health check failed"
echo ""

# Test 2: Root endpoint
echo "2. Testing Root Endpoint..."
curl -s "$BASE_URL/" | jq '.status' && echo "✅ Root endpoint passed" || echo "❌ Root endpoint failed"
echo ""

# Test 3: Admin Stats
echo "3. Testing Admin Stats..."
curl -s "$BASE_URL/admin/stats" | jq '.total_sessions' && echo "✅ Admin stats passed" || echo "❌ Admin stats failed"
echo ""

# Test 4: Active Sessions
echo "4. Testing Active Sessions..."
curl -s "$BASE_URL/sessions/active/list" | jq 'length' && echo "✅ Active sessions passed" || echo "❌ Active sessions failed"
echo ""

# Test 5: Student Registration
echo "5. Testing Student Registration..."
STUDENT_DATA=$(curl -s -X POST "$BASE_URL/students/register" \
  -H "Content-Type: application/json" \
  -d '{"name":"Test Student","email":"test-'$(date +%s)'@example.com"}')

STUDENT_ID=$(echo $STUDENT_DATA | jq -r '.student_id')
echo "Student ID: $STUDENT_ID"
if [ ! -z "$STUDENT_ID" ] && [ "$STUDENT_ID" != "null" ]; then
  echo "✅ Student registration passed"
else
  echo "❌ Student registration failed"
fi
echo ""

echo "========================================"
echo "🎉 API Test Complete!"
echo ""
echo "Frontend URL: https://codeimporter.preview.emergentagent.com"
echo "Backend API: $BASE_URL"
echo ""
