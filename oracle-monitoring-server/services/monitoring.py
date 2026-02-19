from core.database import get_db_metrics
import datetime

class MonitoringService:
    async def get_dashboard_data(self):
        """Aggregate data for main dashboard"""
        base_metrics = await get_db_metrics()
        
        # Add timestamp
        base_metrics["timestamp"] = datetime.datetime.now().isoformat()
        
        # Add derived metrics if not present
        if "health_status" not in base_metrics:
            load = base_metrics.get("cpu_load", 0)
            if load > 90:
                base_metrics["health_status"] = "CRITICAL"
            elif load > 70:
                base_metrics["health_status"] = "WARNING"
            else:
                base_metrics["health_status"] = "HEALTHY"
                
        return base_metrics
