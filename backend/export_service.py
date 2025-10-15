"""
Export Service for Violations
Handles CSV and PDF export of violation data
"""
import csv
import io
import base64
from typing import List, Dict
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class ExportService:
    
    @staticmethod
    def export_violations_csv(violations: List[Dict]) -> str:
        """Export violations to CSV format"""
        try:
            output = io.StringIO()
            
            if not violations:
                return ""
            
            # Define CSV headers
            headers = [
                'Violation ID', 'Student ID', 'Student Name', 'Session ID',
                'Violation Type', 'Severity', 'Message', 'Timestamp',
                'Snapshot URL'
            ]
            
            writer = csv.DictWriter(output, fieldnames=headers)
            writer.writeheader()
            
            for v in violations:
                writer.writerow({
                    'Violation ID': v.get('id', ''),
                    'Student ID': v.get('student_id', ''),
                    'Student Name': v.get('student_name', ''),
                    'Session ID': v.get('session_id', ''),
                    'Violation Type': v.get('violation_type', ''),
                    'Severity': v.get('severity', ''),
                    'Message': v.get('message', ''),
                    'Timestamp': v.get('timestamp', ''),
                    'Snapshot URL': v.get('snapshot_url', '')
                })
            
            return output.getvalue()
        except Exception as e:
            logger.error(f"CSV export error: {e}")
            return ""
    
    @staticmethod
    def export_summary_csv(sessions: List[Dict], violations: List[Dict], students: List[Dict]) -> str:
        """Export summary statistics to CSV"""
        try:
            output = io.StringIO()
            
            # Summary statistics
            output.write("EXAM PROCTORING SUMMARY REPORT\n")
            output.write(f"Generated: {datetime.utcnow().isoformat()}\n\n")
            
            output.write("OVERALL STATISTICS\n")
            output.write(f"Total Students,{len(students)}\n")
            output.write(f"Total Sessions,{len(sessions)}\n")
            output.write(f"Total Violations,{len(violations)}\n\n")
            
            # Violation breakdown
            output.write("VIOLATION BREAKDOWN\n")
            violation_types = {}
            for v in violations:
                v_type = v.get('violation_type', 'unknown')
                violation_types[v_type] = violation_types.get(v_type, 0) + 1
            
            output.write("Violation Type,Count\n")
            for v_type, count in sorted(violation_types.items()):
                output.write(f"{v_type},{count}\n")
            
            output.write("\n")
            
            # Student-wise summary
            output.write("STUDENT-WISE SUMMARY\n")
            output.write("Student ID,Student Name,Total Violations\n")
            
            student_violations = {}
            for v in violations:
                student_id = v.get('student_id', '')
                student_name = v.get('student_name', '')
                key = f"{student_id}|{student_name}"
                student_violations[key] = student_violations.get(key, 0) + 1
            
            for key, count in sorted(student_violations.items(), key=lambda x: x[1], reverse=True):
                student_id, student_name = key.split('|')
                output.write(f"{student_id},{student_name},{count}\n")
            
            return output.getvalue()
        except Exception as e:
            logger.error(f"Summary CSV export error: {e}")
            return ""
    
    @staticmethod
    def generate_html_report(sessions: List[Dict], violations: List[Dict], students: List[Dict]) -> str:
        """Generate HTML report (can be converted to PDF)"""
        try:
            # Violation breakdown
            violation_types = {}
            for v in violations:
                v_type = v.get('violation_type', 'unknown')
                violation_types[v_type] = violation_types.get(v_type, 0) + 1
            
            # Student-wise summary
            student_violations = {}
            for v in violations:
                student_id = v.get('student_id', '')
                student_name = v.get('student_name', '')
                key = f"{student_id}|{student_name}"
                student_violations[key] = student_violations.get(key, 0) + 1
            
            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>Exam Proctoring Report</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 40px; }}
                    h1 {{ color: #333; border-bottom: 2px solid #333; padding-bottom: 10px; }}
                    h2 {{ color: #666; margin-top: 30px; }}
                    table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
                    th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
                    th {{ background-color: #4CAF50; color: white; }}
                    tr:nth-child(even) {{ background-color: #f2f2f2; }}
                    .stat-box {{ display: inline-block; margin: 10px; padding: 20px; border: 2px solid #4CAF50; border-radius: 5px; min-width: 150px; }}
                    .stat-number {{ font-size: 36px; font-weight: bold; color: #4CAF50; }}
                    .stat-label {{ color: #666; font-size: 14px; }}
                </style>
            </head>
            <body>
                <h1>Exam Proctoring Summary Report</h1>
                <p><strong>Generated:</strong> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
                
                <h2>Overall Statistics</h2>
                <div class="stat-box">
                    <div class="stat-number">{len(students)}</div>
                    <div class="stat-label">Total Students</div>
                </div>
                <div class="stat-box">
                    <div class="stat-number">{len(sessions)}</div>
                    <div class="stat-label">Total Sessions</div>
                </div>
                <div class="stat-box">
                    <div class="stat-number">{len(violations)}</div>
                    <div class="stat-label">Total Violations</div>
                </div>
                
                <h2>Violation Breakdown</h2>
                <table>
                    <tr>
                        <th>Violation Type</th>
                        <th>Count</th>
                    </tr>
            """
            
            for v_type, count in sorted(violation_types.items(), key=lambda x: x[1], reverse=True):
                html += f"""
                    <tr>
                        <td>{v_type.replace('_', ' ').title()}</td>
                        <td>{count}</td>
                    </tr>
                """
            
            html += """
                </table>
                
                <h2>Student-wise Summary</h2>
                <table>
                    <tr>
                        <th>Student ID</th>
                        <th>Student Name</th>
                        <th>Total Violations</th>
                    </tr>
            """
            
            for key, count in sorted(student_violations.items(), key=lambda x: x[1], reverse=True):
                student_id, student_name = key.split('|')
                html += f"""
                    <tr>
                        <td>{student_id}</td>
                        <td>{student_name}</td>
                        <td>{count}</td>
                    </tr>
                """
            
            html += """
                </table>
            </body>
            </html>
            """
            
            return html
        except Exception as e:
            logger.error(f"HTML report generation error: {e}")
            return ""

# Global instance
export_service = ExportService()
