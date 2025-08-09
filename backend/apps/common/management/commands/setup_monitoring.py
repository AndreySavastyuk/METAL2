"""
Management command to set up monitoring and logging configuration
"""

import os
from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.management import call_command


class Command(BaseCommand):
    help = 'Set up monitoring, metrics collection, and structured logging'

    def add_arguments(self, parser):
        parser.add_argument(
            '--update-settings',
            action='store_true',
            help='Update Django settings with monitoring configuration',
        )
        parser.add_argument(
            '--create-log-dirs',
            action='store_true',
            help='Create log directories if they don\'t exist',
        )
        parser.add_argument(
            '--test-metrics',
            action='store_true',
            help='Test metrics collection',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Setting up MetalQMS monitoring system...')
        )

        if options['create_log_dirs']:
            self.create_log_directories()

        if options['update_settings']:
            self.update_settings()

        if options['test_metrics']:
            self.test_metrics()

        self.setup_prometheus_metrics()
        self.configure_structured_logging()
        
        self.stdout.write(
            self.style.SUCCESS('Monitoring setup completed successfully!')
        )

    def create_log_directories(self):
        """Create log directories if they don't exist"""
        self.stdout.write('Creating log directories...')
        
        log_dirs = [
            'logs',
            'logs/business_metrics',
            'logs/audit',
            'logs/security',
        ]
        
        for log_dir in log_dirs:
            os.makedirs(log_dir, exist_ok=True)
            self.stdout.write(f'  Created: {log_dir}')

    def update_settings(self):
        """Update Django settings with monitoring configuration"""
        self.stdout.write('Updating Django settings...')
        
        # This would typically modify the settings file or environment
        # For now, we'll just show what needs to be added
        
        settings_additions = """
# Add to INSTALLED_APPS:
'django_prometheus',
'apps.common',

# Add to MIDDLEWARE (at the beginning and end):
'django_prometheus.middleware.PrometheusBeforeMiddleware',
'apps.common.monitoring_middleware.CorrelationIdMiddleware',
'apps.common.monitoring_middleware.PrometheusMonitoringMiddleware',
'apps.common.monitoring_middleware.BusinessMetricsMiddleware',
'apps.common.monitoring_middleware.ErrorTrackingMiddleware',
# ... other middleware ...
'django_prometheus.middleware.PrometheusAfterMiddleware',

# Add to LOGGING configuration:
# (see config/monitoring_settings.py for complete configuration)
"""
        
        self.stdout.write(self.style.WARNING(
            'Manual settings update required. Add the following to your settings:'
        ))
        self.stdout.write(settings_additions)

    def setup_prometheus_metrics(self):
        """Initialize Prometheus metrics collection"""
        self.stdout.write('Setting up Prometheus metrics...')
        
        try:
            from apps.common.monitoring import (
                MetricsCollector,
                app_info,
                system_health
            )
            
            # Initialize metrics
            MetricsCollector.update_active_users()
            MetricsCollector.update_pending_materials()
            MetricsCollector.update_system_health()
            
            # Set initial health status
            system_health.labels(component='django').set(1)
            
            self.stdout.write('  Prometheus metrics initialized')
            
        except ImportError as e:
            self.stdout.write(
                self.style.ERROR(f'Failed to import monitoring module: {e}')
            )

    def configure_structured_logging(self):
        """Configure structured logging"""
        self.stdout.write('Configuring structured logging...')
        
        try:
            import structlog
            
            # Test structured logging
            logger = structlog.get_logger(__name__)
            logger.info(
                "monitoring_setup_completed",
                component="management_command",
                setup_stage="structured_logging"
            )
            
            self.stdout.write('  Structured logging configured')
            
        except ImportError as e:
            self.stdout.write(
                self.style.ERROR(f'Failed to configure structured logging: {e}')
            )

    def test_metrics(self):
        """Test metrics collection functionality"""
        self.stdout.write('Testing metrics collection...')
        
        try:
            from apps.common.monitoring import (
                track_material_processing,
                track_inspection,
                track_lab_test,
                track_certificate_processing,
                MetricsCollector
            )
            
            # Test business metrics
            track_material_processing('40X', 'TestSupplier', 'received')
            track_inspection('visual', 'passed', 'test_inspector', 300.0)
            track_lab_test('chemical_analysis', 'passed', 1800.0)
            track_certificate_processing('success', 'pdf', 5.0)
            
            # Test system metrics
            MetricsCollector.update_system_health()
            
            self.stdout.write('  Metrics collection test completed')
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Metrics test failed: {e}')
            )

    def display_monitoring_info(self):
        """Display information about monitoring setup"""
        info = """
MetalQMS Monitoring Setup Complete!

Available endpoints:
- /metrics/ - Prometheus metrics
- /health/ - Basic health check
- /health/detailed/ - Detailed health check with components
- /health/ready/ - Readiness probe
- /health/live/ - Liveness probe
- /health/metrics-summary/ - Business metrics summary

Grafana dashboards:
- System Overview - Overall system performance
- Business Metrics - Material processing and QC metrics
- Backup Monitoring - Database backup status

Log files (JSON format):
- logs/app.json.log - Application logs
- logs/business_metrics.json.log - Business event logs
- logs/audit.json.log - Audit trail
- logs/error.log - Error logs

Prometheus metrics include:
- HTTP request metrics (rate, duration, errors)
- Database query metrics
- Active user counts
- Material processing counters
- Inspection and lab test metrics
- System health indicators

For more information, see:
- backend/config/monitoring_settings.py
- monitoring/prometheus/prometheus.yml
- monitoring/grafana/dashboards/
"""
        
        self.stdout.write(self.style.SUCCESS(info))