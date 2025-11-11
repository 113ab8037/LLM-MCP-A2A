#!/usr/bin/env python3
"""
Integration tests for the MCP weather server with the real Open-Meteo API.
These tests make real HTTP requests to the API.
"""

import pytest
import asyncio
import sys
import os

# Add the parent folder to the path for importing server.py
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server import (
    get_city_coordinates,
    get_weather_data,
    get_today_weather,
    get_weekly_forecast
)


# Setting up an event loop for tests
@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the entire test session"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
def cleanup_http_client():
    """Close the HTTP client after all tests"""
    yield
    # The HTTP client will be closed automatically when the process terminates.

class TestRealAPIIntegration:
    """Integration tests with a real API"""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_real_city_coordinates(self):
        """Test of obtaining coordinates of a real city"""
        result = await get_city_coordinates("Moscow")
        
        assert result is not None
        latitude, longitude = result
        
        # ПWe check that the coordinates of Moscow are approximately correct.
        assert 55.0 < latitude < 56.0
        assert 37.0 < longitude < 38.0
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_real_weather_data(self):
        """Test of obtaining real weather data"""
        # We use Moscow coordinates
        result = await get_weather_data(55.7558, 37.6176, 1)
        
        assert "current" in result
        assert "daily" in result
        assert "temperature_2m" in result["current"]
        assert "weather_code" in result["current"]
        assert len(result["daily"]["time"]) == 1
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_real_today_weather(self):
        """Test to get real weather for today"""
        result = await get_today_weather("Paris")
        
        assert "Paris" in result
        assert "°C" in result
        assert "Coordinates:" in result
        assert "Open-Meteo API" in result
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_real_weekly_forecast(self):
        """Test of obtaining a real weekly forecast"""
        result = await get_weekly_forecast("Paris")
        
        assert "Paris" in result
        assert "forecast" in result.lower()
        assert "Open-Meteo API" in result
        
        # Проверяем что есть данные на несколько дней
        days_found = result.count("📆")
        assert days_found >= 3  # Минимум 3 дня должно быть
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_unicode_cities_real(self):
        """Real Unicode Cities Quiz"""
        cities = ["Moscow", "Berlin", "Tokyo"]
        
        for city in cities:
            try:
                result = await get_today_weather(city)
                assert city in result or city.title() in result
                assert "°C" in result
            except Exception as e:
                pytest.fail(f"Ошибка для города {city}: {e}")
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_invalid_city_real(self):
        """Test with a non-existent city"""
        from mcp.shared.exceptions import McpError
        
        with pytest.raises(McpError):
            await get_today_weather("Non-existentCity12345XYZ")


class TestPerformance:
    """Performance tests"""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.slow
    async def test_multiple_cities_performance(self):
        """Multi-city performance test"""
        cities = ["Moscow", "London", "Paris", "Tokyo", "New York"]
        
        start_time = asyncio.get_event_loop().time()
        
        # We make requests sequentially
        for city in cities:
            try:
                result = await get_today_weather(city)
                assert city in result
            except Exception as e:
                pytest.fail(f"Error for the city {city}: {e}")
        
        end_time = asyncio.get_event_loop().time()
        total_time = end_time - start_time
        
        # Проверяем что все запросы выполнились за разумное время
        assert total_time < 30  # Максимум 30 секунд на 5 городов
        
        print(f"Execution time for {len(cities)} cities: {total_time:.2f}s")


if __name__ == "__main__":
    # Run only integration tests
    pytest.main([
        __file__, 
        "-v", 
        "-m", "integration",
        "--tb=short"
    ]) 