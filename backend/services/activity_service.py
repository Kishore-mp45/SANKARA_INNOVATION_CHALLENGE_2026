from datetime import datetime
import csv
import io
from typing import List, Dict, Optional

class ActivityService:
    """
    Service to manage real-time activity logs for the Admin Dashboard.
    Uses an in-memory storage (list) to avoid database schema changes.
    """
    
    # In-memory storage for recent logs (Circular buffer behavior)
    _logs: List[Dict] = []
    MAX_LOGS = 100

    @classmethod
    def logs(cls) -> List[Dict]:
        return cls._logs

    @classmethod
    def add_log(cls, action: str, details: str, severity: str = "info", role: str = "system", user_id: str = "System"):
        """
        Add a new log entry.
        Severity: info, success, warning, error, critical
        """
        entry = {
            "id": int(datetime.now().timestamp() * 1000), # Simple unique ID logic
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "details": details,
            "severity": severity,
            "role": role,
            "user_id": user_id
        }
        
        # Add to beginning (newest first)
        cls._logs.insert(0, entry)
        
        # Keep only MAX_LOGS
        if len(cls._logs) > cls.MAX_LOGS:
            cls._logs.pop()
            
        return entry

    @classmethod
    def get_logs(cls, limit: int = 100, role: Optional[str] = None, severity: Optional[str] = None) -> List[Dict]:
        """Get filtered logs."""
        filtered = cls._logs
        if role:
            filtered = [l for l in filtered if l['role'].lower() == role.lower()]
        if severity:
            filtered = [l for l in filtered if l['severity'].lower() == severity.lower()]
            
        return filtered[:limit]

    @classmethod
    def export_logs_csv(cls) -> str:
        """Export logs to CSV string."""
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow(['Timestamp', 'Severity', 'Role', 'User', 'Action', 'Details'])
        
        for log in cls._logs:
            writer.writerow([
                log['timestamp'],
                log['severity'],
                log['role'],
                log['user_id'],
                log['action'],
                log['details']
            ])
            
        return output.getvalue()

    @classmethod
    def clear_logs(cls):
        cls._logs = []
