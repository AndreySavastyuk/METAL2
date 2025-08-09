#!/usr/bin/env python
"""
Test runner script for MetalQMS with coverage reporting
"""
import os
import sys
import subprocess
from pathlib import Path

# Add project directory to Python path
project_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_dir))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tests.test_settings')

import django
django.setup()


def run_tests():
    """Run tests with coverage"""
    print("🧪 Running MetalQMS Tests with Coverage")
    print("=" * 50)
    
    # Test commands
    commands = [
        # Run model tests
        [
            'python', '-m', 'pytest', 
            'tests/test_models.py',
            '-v',
            '--tb=short'
        ],
        
        # Run API tests  
        [
            'python', '-m', 'pytest',
            'tests/test_api.py',
            '-v',
            '--tb=short'
        ],
        
        # Run service tests
        [
            'python', '-m', 'pytest',
            'tests/test_services.py', 
            '-v',
            '--tb=short'
        ],
        
        # Run all tests with coverage
        [
            'python', '-m', 'pytest',
            'tests/',
            '--cov=apps',
            '--cov-report=html:htmlcov',
            '--cov-report=term-missing',
            '--cov-fail-under=80',
            '-v'
        ]
    ]
    
    for i, cmd in enumerate(commands, 1):
        print(f"\n📋 Step {i}/{len(commands)}: {' '.join(cmd[3:])}")
        print("-" * 40)
        
        try:
            result = subprocess.run(cmd, cwd=project_dir, check=True)
            print(f"✅ Step {i} completed successfully")
        except subprocess.CalledProcessError as e:
            print(f"❌ Step {i} failed with exit code {e.returncode}")
            if i < len(commands):
                print("⏭️  Continuing with next step...")
            continue
        except KeyboardInterrupt:
            print("\n⚠️  Tests interrupted by user")
            sys.exit(1)
    
    print("\n🎯 Test Summary")
    print("=" * 50)
    print("✅ All test suites completed")
    print("📊 Coverage report generated in htmlcov/")
    print("🌐 Open htmlcov/index.html to view detailed coverage")


def run_specific_tests():
    """Run specific test categories"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Run MetalQMS tests')
    parser.add_argument('--models', action='store_true', help='Run model tests only')
    parser.add_argument('--api', action='store_true', help='Run API tests only')
    parser.add_argument('--services', action='store_true', help='Run service tests only')
    parser.add_argument('--integration', action='store_true', help='Run integration tests only')
    parser.add_argument('--coverage', action='store_true', help='Run with coverage report')
    parser.add_argument('--fast', action='store_true', help='Run fast tests only')
    
    args = parser.parse_args()
    
    base_cmd = ['python', '-m', 'pytest']
    
    if args.models:
        base_cmd.append('tests/test_models.py')
    elif args.api:
        base_cmd.append('tests/test_api.py')
    elif args.services:
        base_cmd.append('tests/test_services.py')
    elif args.integration:
        base_cmd.extend(['-m', 'integration'])
    else:
        base_cmd.append('tests/')
    
    if args.fast:
        base_cmd.extend(['-m', 'not slow'])
    
    if args.coverage:
        base_cmd.extend([
            '--cov=apps',
            '--cov-report=html:htmlcov',
            '--cov-report=term-missing'
        ])
    
    base_cmd.extend(['-v', '--tb=short'])
    
    print(f"🧪 Running: {' '.join(base_cmd)}")
    print("=" * 50)
    
    try:
        subprocess.run(base_cmd, cwd=project_dir, check=True)
        print("✅ Tests completed successfully")
    except subprocess.CalledProcessError as e:
        print(f"❌ Tests failed with exit code {e.returncode}")
        sys.exit(e.returncode)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        run_specific_tests()
    else:
        run_tests()