#!/usr/bin/env python3
"""
Script for running MCP weather server tests.
"""

import subprocess
import sys


def run_unit_tests():
    """Running quick unit tests with mocks"""
    print("🧪 Running unit tests (with mocks)...")
    result = subprocess.run([
        sys.executable, "-m", "pytest", 
        "test_weather_api.py", 
        "-v", "--tb=short"
    ])
    return result.returncode == 0


def run_integration_tests():
    """Running integration tests against a real API"""
    print("🌐 Running integration tests (real API)...")
    result = subprocess.run([
        sys.executable, "-m", "pytest", 
        "test_integration.py", 
        "-v", "--tb=short", "-m", "integration"
    ])
    return result.returncode == 0


def run_demo_tests():
    """Running demo tests"""
    print("🎬 Running demo tests...")
    result = subprocess.run([sys.executable, "test_tools.py"])
    return result.returncode == 0


def run_all_tests():
    """Запуск всех тестов"""
    print("🔄 Run all tests...")
    result = subprocess.run([
        sys.executable, "-m", "pytest", 
        "-v", "--tb=short", 
        "--cov=server",
        "--cov-report=term-missing"
    ])
    return result.returncode == 0


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Running MCP Weather Server Tests"
    )
    parser.add_argument(
        "--type", 
        choices=["unit", "integration", "demo", "all"], 
        default="unit",
        help="Тип тестов для запуска"
    )
    
    args = parser.parse_args()
    
    print("🌤️ Testing the MCP weather server with the Open-Meteo API")
    print("=" * 60)
    
    success = False
    
    if args.type == "unit":
        success = run_unit_tests()
    elif args.type == "integration":
        success = run_integration_tests()
    elif args.type == "demo":
        success = run_demo_tests()
    elif args.type == "all":
        success = run_all_tests()
    
    if success:
        print("\n✅ All tests were successful!")
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main() 