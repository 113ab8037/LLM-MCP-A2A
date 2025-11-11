#!/usr/bin/env python3
"""
Pytest tests for MCP weather server with Open-Meteo API integration.
"""

import pytest
import sys
import os
from unittest.mock import patch, Mock

# Add the parent folder to the path for importing server.py
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx
from mcp.shared.exceptions import McpError
from mcp.types import INVALID_PARAMS, INTERNAL_ERROR
from server import (
    get_city_coordinates,
    get_weather_data,
    weather_code_to_description,
    get_real_weather_data,
    get_today_weather,
    get_weekly_forecast
)


# Mock data for tests
MOCK_GEOCODING_RESPONSE = {
    "results": [
        {
            "id": 524901,
            "name": "Moscow",
            "latitude": 55.7558,
            "longitude": 37.6176,
            "elevation": 144.0,
            "feature_code": "PPLC",
            "country_code": "RU",
            "admin1_id": 524894,
            "country": "Russia",
            "admin1": "Moscow"
        }
    ]
}

MOCK_WEATHER_RESPONSE = {
    "latitude": 55.7558,
    "longitude": 37.6176,
    "timezone": "Europe/Moscow",
    "elevation": 144.0,
    "current": {
        "time": "2024-01-15T12:00:00Z",
        "temperature_2m": -5.2,
        "relative_humidity_2m": 78,
        "weather_code": 3,
        "wind_speed_10m": 4.5,
        "surface_pressure": 1013.2
    },
    "daily": {
        "time": ["2024-01-15", "2024-01-16", "2024-01-17"],
        "weather_code": [3, 61, 0],
        "temperature_2m_max": [-2.1, 0.5, 2.3],
        "temperature_2m_min": [-8.7, -4.2, -1.5],
        "precipitation_probability_max": [20, 80, 10],
        "wind_speed_10m_max": [6.8, 8.1, 4.2]
    }
}


class TestCityCoordinates:
    """Tests to obtain city coordinates"""
    
    @pytest.mark.asyncio
    async def test_get_city_coordinates_success(self):
        """Test of successful receipt of coordinates"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = MOCK_GEOCODING_RESPONSE
            mock_response.raise_for_status.return_value = None
            
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
            
            result = await get_city_coordinates("Moscow")
            
            assert result is not None
            assert result == (55.7558, 37.6176)
    
    @pytest.mark.asyncio
    async def test_get_city_coordinates_not_found(self):
        """Test when the city is not found"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = {"results": []}
            mock_response.raise_for_status.return_value = None
            
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
            
            result = await get_city_coordinates("UnknownCity")
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_get_city_coordinates_http_error(self):
        """HTTP error handling test"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get.side_effect = httpx.HTTPStatusError(
                "404 Not Found", 
                request=Mock(), 
                response=Mock()
            )
            
            result = await get_city_coordinates("Moscow")
            
            assert result is None


class TestWeatherData:
    """Тесты для получения данных о погоде"""
    
    @pytest.mark.asyncio
    async def test_get_weather_data_success(self):
        """Test of successful weather data retrieval"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = MOCK_WEATHER_RESPONSE
            mock_response.raise_for_status.return_value = None
            
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
            
            result = await get_weather_data(55.7558, 37.6176, 3)
            
            assert result == MOCK_WEATHER_RESPONSE
    
    @pytest.mark.asyncio
    async def test_get_weather_data_http_error(self):
        """Testing HTTP error handling when retrieving weather"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get.side_effect = httpx.HTTPStatusError(
                "500 Internal Server Error",
                request=Mock(),
                response=Mock()
            )
            
            with pytest.raises(httpx.HTTPStatusError):
                await get_weather_data(55.7558, 37.6176, 1)


class TestWeatherCodeConversion:
    """Weather code conversion tests"""
    
    def test_weather_code_to_description_known_codes(self):
        """Test conversion of known codes"""
        assert weather_code_to_description(0) == "clear"
        assert weather_code_to_description(3) == "cloudy"
        assert weather_code_to_description(61) == "light rain"
        assert weather_code_to_description(95) == "storm"
    
    def test_weather_code_to_description_unknown_code(self):
        """Unknown code conversion test"""
        result = weather_code_to_description(999)
        assert "unknown (code 999)" in result


class TestRealWeatherData:
    """Tests to obtain real weather data"""
    
    @pytest.mark.asyncio
    async def test_get_real_weather_data_success(self):
        """Test of successful acquisition of real data"""
        with patch('server.get_city_coordinates') as mock_coords, \
             patch('server.get_weather_data') as mock_weather:
            
            mock_coords.return_value = (55.7558, 37.6176)
            mock_weather.return_value = MOCK_WEATHER_RESPONSE
            
            result = await get_real_weather_data("Moscow", 3)
            
            assert result['city'] == "Moscow"
            assert result['coordinates'] == {
                "latitude": 55.7558, 
                "longitude": 37.6176
            }
            assert len(result['forecast']) == 3
            assert result['current_weather']['temperature'] == -5
            assert result['current_weather']['condition'] == "cloudy"
    
    @pytest.mark.asyncio
    async def test_get_real_weather_data_city_not_found(self):
        """Test when the city is not found"""
        with patch('server.get_city_coordinates') as mock_coords:
            mock_coords.return_value = None
            
            with pytest.raises(McpError) as exc_info:
                await get_real_weather_data("UnknownCity", 1)
            
            assert exc_info.value.error.code == INVALID_PARAMS
            assert "not found" in exc_info.value.error.message


class TestMCPTools:
    """Тесты для MCP инструментов"""
    
    @pytest.mark.asyncio
    async def test_get_today_weather_success(self):
        """Test of successful retrieval of today's weather"""
        mock_weather_data = {
            'city': 'Moscow',
            'coordinates': {'latitude': 55.7558, 'longitude': 37.6176},
            'current_time': '2024-01-15 12:00 UTC',
            'current_weather': {
                'temperature': -5,
                'condition': 'пасмурно',
                'humidity': 78,
                'wind_speed': 4,
                'pressure': 1013
            },
            'forecast': [{
                'date': '2024-01-15',
                'weekday': 'Monday',
                'day_temp': -2,
                'night_temp': -9,
                'condition': 'пасмурно',
                'wind_speed': 7,
                'precipitation_chance': 20
            }]
        }
        
        with patch('server.get_real_weather_data') as mock_data:
            mock_data.return_value = mock_weather_data
            
            result = await get_today_weather("Moscow")
            
            assert "Moscow" in result
            assert "-5°C" in result
            assert "cloudy" in result
            assert "Open-Meteo API" in result
    
    @pytest.mark.asyncio
    async def test_get_today_weather_empty_city(self):
        """Empty city name test"""
        with pytest.raises(McpError) as exc_info:
            await get_today_weather("")
        
        assert exc_info.value.error.code == INVALID_PARAMS
        assert "empty" in exc_info.value.error.message
    
    @pytest.mark.asyncio
    async def test_get_weekly_forecast_success(self):
        """Тест успешного получения недельного прогноза"""
        mock_weather_data = {
            'city': 'London',
            'coordinates': {'latitude': 51.5074, 'longitude': -0.1278},
            'current_time': '2024-01-15 12:00 UTC',
            'current_weather': {
                'temperature': 8,
                'condition': 'облачно',
                'humidity': 85,
                'wind_speed': 6,
                'pressure': 1015
            },
            'forecast': [
                {
                    'date': '2024-01-15',
                    'weekday': 'Monday',
                    'day_temp': 10,
                    'night_temp': 5,
                    'condition': 'облачно',
                    'wind_speed': 8,
                    'precipitation_chance': 40
                },
                {
                    'date': '2024-01-16',
                    'weekday': 'Tuesday',
                    'day_temp': 12,
                    'night_temp': 7,
                    'condition': 'дождь',
                    'wind_speed': 10,
                    'precipitation_chance': 70
                }
            ]
        }
        
        with patch('server.get_real_weather_data') as mock_data:
            mock_data.return_value = mock_weather_data
            
            result = await get_weekly_forecast("London")
            
            assert "London" in result
            assert "прогноз" in result.lower()
            assert "Open-Meteo API" in result
    
    @pytest.mark.asyncio
    async def test_get_weekly_forecast_whitespace_city(self):
        """City name test with spaces"""
        with pytest.raises(McpError) as exc_info:
            await get_weekly_forecast("   ")
        
        assert exc_info.value.error.code == INVALID_PARAMS


class TestIntegration:
    """Integration tests"""
    
    @pytest.mark.asyncio
    async def test_full_weather_flow(self):
        """Testing the full weather stream"""
        with patch('httpx.AsyncClient') as mock_client:
            # Setting up mocks for two calls: geocoding and weather
            mock_responses = [
                Mock(json=lambda: MOCK_GEOCODING_RESPONSE),
                Mock(json=lambda: MOCK_WEATHER_RESPONSE)
            ]
            
            for mock_response in mock_responses:
                mock_response.raise_for_status.return_value = None
            
            mock_client.return_value.__aenter__.return_value.get.side_effect = mock_responses
            
            result = await get_today_weather("Moscow")
            
            # We check that the result contains the expected data.
            assert "Moscow" in result
            assert "55.76" in result  # Координаты
            assert "37.62" in result
            assert "-5°C" in result   # Температура
            assert "пасмурно" in result  # Условия
            assert "78%" in result    # Влажность
    
    @pytest.mark.asyncio
    async def test_error_propagation(self):
        """Test of error propagation through the entire chain"""
        with patch('server.get_city_coordinates') as mock_coords:
            mock_coords.side_effect = Exception("Network error")
            
            with pytest.raises(McpError) as exc_info:
                await get_today_weather("Moscow")
            
            assert exc_info.value.error.code == INTERNAL_ERROR
            assert "Network error" in exc_info.value.error.message


class TestEdgeCases:
    """Edge case tests"""
    
    @pytest.mark.asyncio
    async def test_unicode_city_names(self):
        """City Names Unicode Test"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = MOCK_GEOCODING_RESPONSE
            mock_response.raise_for_status.return_value = None
            
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
            
            # Тестируем различные unicode символы
            unicode_cities = ["Москва", "北京", "العربية", "München"]
            
            for city in unicode_cities:
                result = await get_city_coordinates(city)
                # Так как мы мокируем ответ, все города вернут один результат
                assert result == (55.7558, 37.6176)
    
    def test_weather_codes_coverage(self):
        """Test coverage of various weather codes"""
        # Тестируем основные категории кодов
        clear_codes = [0, 1]
        cloudy_codes = [2, 3]
        rain_codes = [61, 63, 65]
        snow_codes = [71, 73, 75]
        storm_codes = [95, 96, 99]
        
        for code in clear_codes + cloudy_codes + rain_codes + snow_codes + storm_codes:
            description = weather_code_to_description(code)
            assert isinstance(description, str)
            assert len(description) > 0
            assert "unknown" not in description
        
        # Тестируем неизвестный код
        unknown_description = weather_code_to_description(9999)
        assert "unknown" in unknown_description


if __name__ == "__main__":
    # Запуск тестов с подробным выводом
    pytest.main([__file__, "-v", "--tb=short"]) 