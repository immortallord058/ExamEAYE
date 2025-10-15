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


    @staticmethod
    def export_student_violations_csv(student_id: str, student_name: str, violations: List[Dict]) -> str:
        """Export individual student violations to CSV"""
        try:
            output = io.StringIO()
            
            # Header
            output.write(f"STUDENT VIOLATION REPORT\n")
            output.write(f"Student ID: {student_id}\n")
            output.write(f"Student Name: {student_name}\n")
            output.write(f"Generated: {datetime.utcnow().isoformat()}\n")
            output.write(f"Total Violations: {len(violations)}\n\n")
            
            # Violation breakdown
            violation_types = {}
            for v in violations:
                v_type = v.get('violation_type', 'unknown')
                violation_types[v_type] = violation_types.get(v_type, 0) + 1
            
            output.write("VIOLATION BREAKDOWN\n")
            output.write("Violation Type,Count\n")
            for v_type, count in sorted(violation_types.items()):
                output.write(f"{v_type},{count}\n")
            
            output.write("\n")
            
            # Detailed violations
            output.write("DETAILED VIOLATIONS\n")
            output.write("Timestamp,Violation Type,Severity,Message,Snapshot URL\n")
            
            for v in violations:
                output.write(f"{v.get('timestamp', '')},{v.get('violation_type', '')},{v.get('severity', '')},{v.get('message', '')},{v.get('snapshot_url', '')}\n")
            
            return output.getvalue()
        except Exception as e:
            logger.error(f"Student CSV export error: {e}")
            return ""
    
    @staticmethod
    def generate_student_html_report(student_id: str, student_name: str, violations: List[Dict]) -> str:
        """Generate HTML report for individual student with violation images"""
        try:
            # Violation breakdown
            violation_types = {}
            for v in violations:
                v_type = v.get('violation_type', 'unknown')
                violation_types[v_type] = violation_types.get(v_type, 0) + 1
            
            html = ("""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>Student Violation Report - """ + student_name + """</title>
                <style>"""
                    body { font-family: Arial, sans-serif; margin: 40px; }
                    .header { text-align: center; border-bottom: 3px solid #333; padding-bottom: 20px; margin-bottom: 30px; }
                    h1 { color: #333; margin-bottom: 10px; }
                    .info-box { background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0; }
                    .stat-row { display: flex; justify-content: space-around; margin: 20px 0; }
                    .stat-box { text-align: center; padding: 15px; }
                    .stat-number { font-size: 36px; font-weight: bold; color: #e74c3c; }
                    .stat-label { color: #666; font-size: 14px; margin-top: 5px; }
                    h2 { color: #666; margin-top: 30px; border-bottom: 2px solid #ddd; padding-bottom: 10px; }
                    table { border-collapse: collapse; width: 100%; margin: 20px 0; }
                    th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }
                    th { background-color: #e74c3c; color: white; }
                    tr:nth-child(even) { background-color: #f9f9f9; }
                    .violation-image { max-width: 300px; max-height: 200px; border: 2px solid #e74c3c; border-radius: 5px; margin: 10px 0; }
                    .violation-card { border: 1px solid #ddd; padding: 15px; margin: 15px 0; border-radius: 5px; }
                    .violation-card:nth-child(even) { background-color: #f9f9f9; }
                    .violation-header { font-weight: bold; color: #e74c3c; margin-bottom: 10px; }
                    .timestamp { color: #666; font-size: 12px; }
                </style>
            </head>
            <body>"""
                <div class="header">
                    <h1>Student Violation Report</h1>
                    <p><strong>Student ID:</strong> """ + student_id + """</p>
                    <p><strong>Student Name:</strong> """ + student_name + """</p>
                    <p><strong>Generated:</strong> """ + datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC') + """</p>
                </div>
                
                <div class="stat-row">
                    <div class="stat-box">
                        <div class="stat-number">""" + str(len(violations)) + """</div>
                        <div class="stat-label">Total Violations</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-number">""" + str(len(violation_types)) + """</div>
                        <div class="stat-label">Violation Types</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-number">""" + str(len([v for v in violations if v.get('snapshot_url') or v.get('snapshot_base64')])) + """</div>
                        <div class="stat-label">Evidence Photos</div>
                    </div>
                </div>
                
                <h2>Violation Breakdown</h2>
                <table>
                    <tr>
                        <th>Violation Type</th>
                        <th>Count</th>
                        <th>Percentage</th>
                    </tr>
            """
            
            for v_type, count in sorted(violation_types.items(), key=lambda x: x[1], reverse=True):
                percentage = (count / len(violations)) * 100
                html += """
                    <tr>
                        <td>""" + v_type.replace('_', ' ').title() + """</td>
                        <td>""" + str(count) + """</td>
                        <td>""" + f"{percentage:.1f}" + """%</td>
                    </tr>
                """
            
            html += """
                </table>
                
                <h2>Detailed Violations with Evidence</h2>
            """
            
            for i, v in enumerate(violations, 1):
                timestamp = v.get('timestamp')
                if isinstance(timestamp, str):
                    timestamp_str = timestamp
                else:
                    timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S') if timestamp else 'N/A'
                
                html += """
                <div class="violation-card">
                    <div class="violation-header">Violation #""" + str(i) + """: """ + v.get('violation_type', 'Unknown').replace('_', ' ').title() + """</div>
                    <p><strong>Severity:</strong> """ + v.get('severity', 'N/A').upper() + """</p>
                    <p><strong>Message:</strong> """ + v.get('message', 'N/A') + """</p>
                    <p class="timestamp"><strong>Timestamp:</strong> """ + timestamp_str + """</p>
                """
                
                # Add image if available
                if v.get('snapshot_url'):
                    html += '<img src="' + v.get("snapshot_url") + '" class="violation-image" alt="Violation Evidence">'
                elif v.get('snapshot_base64'):
                    snapshot_base64 = v.get('snapshot_base64')
                    if not snapshot_base64.startswith('data:'):
                        snapshot_base64 = "data:image/jpeg;base64," + snapshot_base64
                    html += '<img src="' + snapshot_base64 + '" class="violation-image" alt="Violation Evidence">'
                
                html += "</div>"
            
            html += """
            </body>
            </html>
            """
            
            return html
        except Exception as e:
            logger.error(f"Student HTML report generation error: {e}")
            return ""

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
