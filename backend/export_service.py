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
                stud_id, stud_name = key.split('|')
                html += f"""
                    <tr>
                        <td>{stud_id}</td>
                        <td>{stud_name}</td>
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
            output.write("Timestamp,Violation Type,Severity,Message\n")
            
            for v in violations:
                output.write(f"{v.get('timestamp', '')},{v.get('violation_type', '')},{v.get('severity', '')},{v.get('message', '')}\n")
            
            return output.getvalue()
        except Exception as e:
            logger.error(f"Student CSV export error: {e}")
            return ""
    
    @staticmethod
    def generate_student_html_report(student_id: str, student_name: str, violations: List[Dict]) -> str:
        """Generate HTML report for individual student with violation images"""
        try:
            # Simple HTML generation without complex string formatting
            html_parts = []
            
            # Violation breakdown
            violation_types = {}
            for v in violations:
                v_type = v.get('violation_type', 'unknown')
                violation_types[v_type] = violation_types.get(v_type, 0) + 1
            
            # Header and styles
            html_parts.append('<!DOCTYPE html><html><head><meta charset="UTF-8">')
            html_parts.append(f'<title>Student Violation Report - {student_name}</title>')
            html_parts.append('<style>body{font-family:Arial,sans-serif;margin:40px;background:#f9f9f9}.header{text-align:center;border-bottom:3px solid #e74c3c;padding-bottom:20px;margin-bottom:30px;background:white;padding:30px;border-radius:10px}h1{color:#e74c3c;margin:0}h2{color:#333;border-bottom:2px solid #e74c3c;padding-bottom:10px;margin-top:30px}table{border-collapse:collapse;width:100%;margin:20px 0;background:white}th,td{border:1px solid #ddd;padding:12px;text-align:left}th{background-color:#e74c3c;color:white}tr:nth-child(even){background:#f9f9f9}.violation-card{border:1px solid #ddd;padding:20px;margin:15px 0;border-radius:5px;background:white}.violation-card:nth-child(even){background:#f9f9f9}.summary-box{background:white;padding:20px;border-radius:8px;margin:20px 0;box-shadow:0 2px 4px rgba(0,0,0,0.1)}.badge{display:inline-block;padding:4px 12px;border-radius:4px;font-size:12px;font-weight:bold}.badge-high{background:#e74c3c;color:white}.badge-medium{background:#f39c12;color:white}.badge-low{background:#3498db;color:white}</style>')
            html_parts.append('</head><body>')
            html_parts.append(f'<div class="header"><h1>Student Violation Report</h1><p><strong>Student ID:</strong> {student_id}</p><p><strong>Student Name:</strong> {student_name}</p><p><strong>Generated:</strong> {datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")}</p></div>')
            
            # Statistics
            html_parts.append(f'<div class="summary-box"><h2>Summary</h2>')
            html_parts.append(f'<p><strong>Total Violations:</strong> {len(violations)}</p>')
            html_parts.append(f'<p><strong>Report Generated:</strong> {datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")}</p>')
            html_parts.append('</div>')
            
            # Violation breakdown table
            html_parts.append('<h2>Violation Breakdown</h2><table><tr><th>Violation Type</th><th>Count</th><th>Percentage</th></tr>')
            for v_type, count in sorted(violation_types.items(), key=lambda x: x[1], reverse=True):
                percentage = (count / len(violations)) * 100 if len(violations) > 0 else 0
                html_parts.append(f'<tr><td>{v_type.replace("_", " ").title()}</td><td>{count}</td><td>{percentage:.1f}%</td></tr>')
            html_parts.append('</table>')
            
            # Detailed violations
            html_parts.append('<h2>Detailed Violations</h2>')
            
            for i, v in enumerate(violations, 1):
                violation_type = v.get('violation_type', 'unknown')
                severity = v.get("severity", "N/A").upper()
                timestamp_str = str(v.get('timestamp', 'N/A'))
                
                # Color-coded severity badge
                badge_class = 'badge-high' if severity == 'HIGH' else 'badge-medium' if severity == 'MEDIUM' else 'badge-low'
                
                html_parts.append(f'<div class="violation-card">')
                html_parts.append(f'<h3>Violation #{i}: {violation_type.replace("_", " ").title()}</h3>')
                html_parts.append(f'<p><strong>Severity:</strong> <span class="badge {badge_class}">{severity}</span></p>')
                html_parts.append(f'<p><strong>Message:</strong> {v.get("message", "N/A")}</p>')
                html_parts.append(f'<p><strong>Timestamp:</strong> {timestamp_str}</p>')
                html_parts.append('</div>')
            
            html_parts.append('</body></html>')
            
            return ''.join(html_parts)
        except Exception as e:
            logger.error(f"Student HTML report generation error: {e}")
            return ""

# Global instance
export_service = ExportService()
