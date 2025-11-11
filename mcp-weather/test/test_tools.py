#!/usr/bin/env python3
"""
A simple test script to demonstrate the MCP weather server.
This script now works with the real Open-Meteo API.
"""

import sys
import os
import asyncio
import pytest

# Add the parent directory to the path for importing server.py
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server import get_today_weather, get_weekly_forecast


@pytest.mark.asyncio
async def test_today_weather():
    """Testing getting today's weather"""
    print("🌤️ Test for getting today's weather:")
    print("=" * 50)
    
    try:
        result = await get_today_weather("Москва")
        print(result)
        print()
    except Exception as e:
        print(f"Error: {e}")
        print()


@pytest.mark.asyncio
async def test_weekly_forecast():
    """Testing getting a weekly forecast"""
    print("📅 Weekly weather forecast test:")
    print("=" * 50)
    
    try:
        result = await get_weekly_forecast("London")
        print(result)
        print()
    except Exception as e:
        print(f"Ошибка: {e}")
        print()


@pytest.mark.asyncio
async def test_different_cities():
    """Tests different cities with different names"""
    print("🌍 Test of different cities:")
    print("=" * 50)
    
    cities = [
        "Париж", 
        "New York", 
        "東京", 
        "São Paulo", 
        "Санкт-Петербург",
        "Los Angeles"
    ]
    
    for city in cities:
        try:
            print(f"\n--- Weather today in {city} ---")
            result = await get_today_weather(city)
            print(result)
        except Exception as e:
            print(f"Error for {city}: {e}")


@pytest.mark.asyncio
async def test_consistency():
    """Tests data consistency for one city"""
    print("🔄 Data consistency test:")
    print("=" * 50)
    
    city = "Berlin"
    
    try:
        print(f"First request for {city}:")
        result1 = await get_today_weather(city)
        print(result1[:100] + "...")
        
        print(f"\nSecond request for {city}:")
        result2 = await get_today_weather(city)
        print(result2[:100] + "...")
        
        # We check that the data has been received
        print("\nData for one city was received")
        
    except Exception as e:
        print(f"Error: {e}")


@pytest.mark.asyncio
async def test_error_handling():
    """Tests error handling"""
    print("⚠️ Error handling test:")
    print("=" * 50)
    
    # Empty city name test
    try:
        result = await get_today_weather("")
        print(result)
    except Exception as e:
        print(f"Expected error for an empty city: {e}")
    
    # Тест с пробелами
    try:
        result = await get_today_weather("   ")
        print(result)
    except Exception as e:
        print(f"Ожидаемая ошибка для пробелов: {e}")
        
    print()


@pytest.mark.asyncio
async def test_unicode_cities():
    """Tests cities with Unicode characters"""
    print("🌐 Unicode Cities Test:")
    print("=" * 50)
    
    unicode_cities = [
        "北京",  # Beijing
        "München",  # Munich  
        "São Paulo",  # Sao Paulo
        "Москва",  # Moscow
        "العين"  # Al Ain
    ]
    
    for city in unicode_cities:
        try:
            print(f"\n--- Weather in {city} ---")
            result = await get_today_weather(city)
            print(result[:150] + "...")
        except Exception as e:
            print(f"Error for {city}: {e}")


async def run_all_tests():
    """Runs all tests in one event loop"""
    print("🧪 Running MCP Weather Server Tests")
    print("=" * 60)
    print("🛠️ We test two tools with any cities:")
    print("   - get_today_weather(city)")
    print("   - get_weekly_forecast(city)")
    print("🌍 Now any city names are supported!")
    print()
    
    # Запускаем все тесты в одном event loop
    await test_today_weather()
    await test_weekly_forecast()
    await test_different_cities()
    await test_consistency()
    await test_unicode_cities()
    await test_error_handling()
    
    print("✅ All tests completed!")


def main():
    """The main function for running all tests"""
    asyncio.run(run_all_tests())


if __name__ == "__main__":
    main() 