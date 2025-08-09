"""
Monitoring and maintenance tasks for MetalQMS
"""

import time
import os
import subprocess
from datetime import datetime, timedelta
from celery import shared_task
from django.utils import timezone
from django.conf import settings
import structlog

from .monitoring import (
    MetricsCollector,
    track_material_processing,
    track_inspection,
    track_lab_test
)

logger = structlog.get_logger(__name__)

@shared_task(bind=True)
def collect_system_metrics(self):
    """
    Periodic task to collect system-wide metrics
    """
    try:
        start_time = time.time()
        
        logger.info(
            "metrics_collection_started",
            task_id=self.request.id,
            component="metrics_collection"
        )
        
        # Update all metrics
        MetricsCollector.update_active_users()
        MetricsCollector.update_pending_materials()
        MetricsCollector.update_system_health()
        
        duration = time.time() - start_time
        
        logger.info(
            "metrics_collection_completed",
            task_id=self.request.id,
            duration=duration,
            component="metrics_collection"
        )
        
        return {
            'status': 'success',
            'duration': duration,
            'timestamp': timezone.now().isoformat()
        }
        
    except Exception as e:
        logger.error(
            "metrics_collection_failed",
            task_id=self.request.id,
            error=str(e),
            component="metrics_collection",
            exc_info=True
        )
        raise self.retry(countdown=60, max_retries=3, exc=e)

@shared_task(bind=True)
def collect_business_metrics(self):
    """
    Collect business-specific metrics from the database
    """
    try:
        from apps.warehouse.models import Material, MaterialReceipt
        from apps.quality.models import QCInspection
        from apps.laboratory.models import LabTestRequest, LabTestResult
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        start_time = time.time()
        
        logger.info(
            "business_metrics_collection_started",
            task_id=self.request.id,
            component="business_metrics"
        )
        
        # Collect current counts
        metrics = {
            'materials_total': Material.objects.count(),
            'materials_pending_qc': MaterialReceipt.objects.filter(status='pending_qc').count(),
            'inspections_in_progress': QCInspection.objects.filter(status='in_progress').count(),
            'lab_tests_pending': LabTestRequest.objects.filter(status__in=['pending', 'assigned']).count(),
            'active_users': User.objects.filter(is_active=True, last_login__gte=timezone.now() - timedelta(hours=24)).count(),
        }
        
        # Log business metrics
        logger.info(
            "business_metrics_snapshot",
            task_id=self.request.id,
            **metrics,
            component="business_metrics"
        )
        
        duration = time.time() - start_time
        
        return {
            'status': 'success',
            'metrics': metrics,
            'duration': duration,
            'timestamp': timezone.now().isoformat()
        }
        
    except Exception as e:
        logger.error(
            "business_metrics_collection_failed",
            task_id=self.request.id,
            error=str(e),
            component="business_metrics",
            exc_info=True
        )
        raise self.retry(countdown=120, max_retries=3, exc=e)

@shared_task(bind=True)
def monitor_backup_status(self):
    """
    Monitor backup status and update metrics
    """
    try:
        backup_dir = '/backups'
        start_time = time.time()
        
        logger.info(
            "backup_monitoring_started",
            task_id=self.request.id,
            backup_dir=backup_dir,
            component="backup_monitoring"
        )
        
        if not os.path.exists(backup_dir):
            logger.warning(
                "backup_directory_not_found",
                task_id=self.request.id,
                backup_dir=backup_dir,
                component="backup_monitoring"
            )
            return {'status': 'warning', 'message': 'Backup directory not found'}
        
        # Find latest backup file
        backup_files = []
        for filename in os.listdir(backup_dir):
            if filename.startswith('metalqms_backup_') and filename.endswith('.tar.gz'):
                filepath = os.path.join(backup_dir, filename)
                stat = os.stat(filepath)
                backup_files.append({
                    'filename': filename,
                    'path': filepath,
                    'size': stat.st_size,
                    'mtime': stat.st_mtime,
                    'created': datetime.fromtimestamp(stat.st_mtime)
                })
        
        if not backup_files:
            logger.warning(
                "no_backup_files_found",
                task_id=self.request.id,
                backup_dir=backup_dir,
                component="backup_monitoring"
            )
            return {'status': 'warning', 'message': 'No backup files found'}
        
        # Sort by modification time
        backup_files.sort(key=lambda x: x['mtime'], reverse=True)
        latest_backup = backup_files[0]
        
        # Calculate time since last backup
        time_since_backup = timezone.now() - timezone.make_aware(latest_backup['created'])
        hours_since_backup = time_since_backup.total_seconds() / 3600
        
        # Update metrics (would need to implement these metrics)
        # metalqms_last_backup_timestamp.set(latest_backup['mtime'])
        # metalqms_backup_size_bytes.set(latest_backup['size'])
        
        backup_status = {
            'latest_backup': latest_backup['filename'],
            'size_bytes': latest_backup['size'],
            'hours_since_backup': hours_since_backup,
            'total_backups': len(backup_files),
            'backup_dir_size': sum(f['size'] for f in backup_files)
        }
        
        # Log backup status
        logger.info(
            "backup_status_updated",
            task_id=self.request.id,
            **backup_status,
            component="backup_monitoring"
        )
        
        # Alert if backup is too old
        if hours_since_backup > 26:  # Allow 2 hours past daily schedule
            logger.warning(
                "backup_overdue",
                task_id=self.request.id,
                hours_since_backup=hours_since_backup,
                component="backup_monitoring"
            )
        
        duration = time.time() - start_time
        
        return {
            'status': 'success',
            'backup_status': backup_status,
            'duration': duration,
            'timestamp': timezone.now().isoformat()
        }
        
    except Exception as e:
        logger.error(
            "backup_monitoring_failed",
            task_id=self.request.id,
            error=str(e),
            component="backup_monitoring",
            exc_info=True
        )
        raise self.retry(countdown=300, max_retries=3, exc=e)

@shared_task(bind=True)
def cleanup_old_logs(self):
    """
    Clean up old log files to prevent disk space issues
    """
    try:
        log_dir = getattr(settings, 'LOG_DIR', 'logs')
        retention_days = 30
        start_time = time.time()
        
        logger.info(
            "log_cleanup_started",
            task_id=self.request.id,
            log_dir=log_dir,
            retention_days=retention_days,
            component="log_cleanup"
        )
        
        if not os.path.exists(log_dir):
            return {'status': 'success', 'message': 'Log directory does not exist'}
        
        cutoff_time = time.time() - (retention_days * 24 * 3600)
        cleaned_files = []
        total_size_freed = 0
        
        for root, dirs, files in os.walk(log_dir):
            for filename in files:
                if filename.endswith('.log') or filename.endswith('.log.gz'):
                    filepath = os.path.join(root, filename)
                    try:
                        stat = os.stat(filepath)
                        if stat.st_mtime < cutoff_time:
                            file_size = stat.st_size
                            os.remove(filepath)
                            cleaned_files.append(filename)
                            total_size_freed += file_size
                    except OSError as e:
                        logger.warning(
                            "failed_to_remove_log_file",
                            task_id=self.request.id,
                            filepath=filepath,
                            error=str(e),
                            component="log_cleanup"
                        )
        
        duration = time.time() - start_time
        
        logger.info(
            "log_cleanup_completed",
            task_id=self.request.id,
            cleaned_files_count=len(cleaned_files),
            total_size_freed=total_size_freed,
            duration=duration,
            component="log_cleanup"
        )
        
        return {
            'status': 'success',
            'cleaned_files': len(cleaned_files),
            'size_freed_bytes': total_size_freed,
            'duration': duration,
            'timestamp': timezone.now().isoformat()
        }
        
    except Exception as e:
        logger.error(
            "log_cleanup_failed",
            task_id=self.request.id,
            error=str(e),
            component="log_cleanup",
            exc_info=True
        )
        raise self.retry(countdown=300, max_retries=2, exc=e)

@shared_task(bind=True)
def health_check_services(self):
    """
    Perform health checks on external services and dependencies
    """
    try:
        from django.db import connection
        from django.core.cache import cache
        
        start_time = time.time()
        health_status = {}
        
        logger.info(
            "health_check_started",
            task_id=self.request.id,
            component="health_check"
        )
        
        # Database health check
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                health_status['database'] = 'healthy' if result and result[0] == 1 else 'unhealthy'
        except Exception as e:
            health_status['database'] = 'unhealthy'
            logger.error(
                "database_health_check_failed",
                task_id=self.request.id,
                error=str(e),
                component="health_check"
            )
        
        # Redis health check
        try:
            cache.set('health_check', 'test', timeout=30)
            cached_value = cache.get('health_check')
            health_status['redis'] = 'healthy' if cached_value == 'test' else 'unhealthy'
        except Exception as e:
            health_status['redis'] = 'unhealthy'
            logger.error(
                "redis_health_check_failed",
                task_id=self.request.id,
                error=str(e),
                component="health_check"
            )
        
        # Celery worker health check
        try:
            from celery import current_app
            inspect = current_app.control.inspect()
            stats = inspect.stats()
            health_status['celery'] = 'healthy' if stats else 'unhealthy'
        except Exception as e:
            health_status['celery'] = 'degraded'
            logger.warning(
                "celery_health_check_failed",
                task_id=self.request.id,
                error=str(e),
                component="health_check"
            )
        
        duration = time.time() - start_time
        overall_health = 'healthy' if all(
            status in ['healthy', 'degraded'] for status in health_status.values()
        ) else 'unhealthy'
        
        logger.info(
            "health_check_completed",
            task_id=self.request.id,
            overall_health=overall_health,
            **health_status,
            duration=duration,
            component="health_check"
        )
        
        return {
            'status': 'success',
            'overall_health': overall_health,
            'component_health': health_status,
            'duration': duration,
            'timestamp': timezone.now().isoformat()
        }
        
    except Exception as e:
        logger.error(
            "health_check_failed",
            task_id=self.request.id,
            error=str(e),
            component="health_check",
            exc_info=True
        )
        raise self.retry(countdown=60, max_retries=3, exc=e)

@shared_task(bind=True)
def generate_daily_report(self):
    """
    Generate daily business metrics report
    """
    try:
        from apps.warehouse.models import Material, MaterialReceipt
        from apps.quality.models import QCInspection
        from apps.laboratory.models import LabTestRequest, LabTestResult
        
        start_time = time.time()
        today = timezone.now().date()
        yesterday = today - timedelta(days=1)
        
        logger.info(
            "daily_report_generation_started",
            task_id=self.request.id,
            report_date=str(yesterday),
            component="daily_report"
        )
        
        # Calculate daily metrics
        daily_metrics = {
            'date': str(yesterday),
            'materials_received': MaterialReceipt.objects.filter(
                receipt_date__date=yesterday
            ).count(),
            'inspections_completed': QCInspection.objects.filter(
                inspection_date__date=yesterday,
                status='completed'
            ).count(),
            'lab_tests_completed': LabTestResult.objects.filter(
                completed_at__date=yesterday
            ).count(),
            'materials_approved': QCInspection.objects.filter(
                inspection_date__date=yesterday,
                status='completed',
                # Add approval conditions
            ).count(),
        }
        
        # Log daily report
        logger.info(
            "daily_business_report",
            task_id=self.request.id,
            **daily_metrics,
            component="daily_report"
        )
        
        duration = time.time() - start_time
        
        return {
            'status': 'success',
            'report': daily_metrics,
            'duration': duration,
            'timestamp': timezone.now().isoformat()
        }
        
    except Exception as e:
        logger.error(
            "daily_report_generation_failed",
            task_id=self.request.id,
            error=str(e),
            component="daily_report",
            exc_info=True
        )
        raise self.retry(countdown=300, max_retries=2, exc=e)