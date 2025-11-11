from datetime import datetime
from typing import Dict, Optional, Tuple
import httpx

import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.routing import Route, Mount

from mcp.server.fastmcp import FastMCP
from mcp.shared.exceptions import McpError
from mcp.types import ErrorData, INTERNAL_ERROR, INVALID_PARAMS
from mcp.server.sse import SseServerTransport

# Create an instance of the MCP server with the identifier "weather"
mcp = FastMCP("weather")


async def get_city_coordinates(
    city_name: str
) -> Optional[Tuple[float, float]]:
    """
    Gets city coordinates via the Open-Meteo Geocoding API.

    Args:
        city_name: City name

    Returns:
        Tuple[latitude, longitude] or None if not found
    """
    try:
        geocoding_url = "https://geocoding-api.open-meteo.com/v1/search"
        params = {
            "name": city_name,
            "count": 1,
            "language": "ru",
            "format": "json"
        }
        
        # Create a new HTTP client for each request
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(geocoding_url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if "results" not in data or not data["results"]:
                return None
                
            result = data["results"][0]
            return result["latitude"], result["longitude"]
        
    except Exception as e:
        print(f"Coordinate error for the city {city_name}: {e}")
        return None


async def get_weather_data(
    latitude: float, 
    longitude: float, 
    days: int = 1
) -> Dict:
    """
    Retrieves weather data via the Open-Meteo API

    Args:
        latitude: Latitude
        longitude: Longitude
        days: Number of forecast days

    Returns:
        Dictionary with weather data
    """
    weather_url = "https://api.open-meteo.com/v1/forecast"
    
    # Параметры для текущей погоды
    current_params = [
        "temperature_2m",
        "relative_humidity_2m", 
        "weather_code",
        "wind_speed_10m",
        "surface_pressure"
    ]
    
    # Параметры для ежедневного прогноза
    daily_params = [
        "weather_code",
        "temperature_2m_max",
        "temperature_2m_min",
        "precipitation_probability_max",
        "wind_speed_10m_max"
    ]
    
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": ",".join(current_params),
        "daily": ",".join(daily_params),
        "timezone": "auto",
        "forecast_days": days
    }
    
    # Создаем новый HTTP клиент для каждого запроса
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(weather_url, params=params)
        response.raise_for_status()
        
        return response.json()


def weather_code_to_description(code: int) -> str:
    """
    Converts a WMO weather code to a text description.

    Args:
        code: WMO weather code

    Returns:
        Text description of the weather in Russian
    """
    weather_codes = {
        0: "clear",
        1: "mostly clear",
        2: "partly cloudy",
        3: "overcast",
        45: "fog",
        48: "drizzle",
        51: "light drizzle",
        53: "moderate drizzle",
        55: "heavy drizzle",
        56: "light freezing drizzle",
        57: "heavy freezing drizzle",
        61: "light rain",
        63: "moderate rain",
        65: "heavy rain",
        66: "light freezing rain",
        67: "heavy freezing rain",
        71: "light snow",
        73: "moderate snow",
        75: "heavy snow",
        77: "snow pellets",
        80: "light showers",
        81: "moderate showers",
        82: "heavy showers",
        85: "light snow showers",
        86: "heavy snow showers",
        95: "thunderstorm",
        96: "thunderstorm with light hail",
        99: "thunderstorm with large hail"
    }
    
    return weather_codes.get(code, f"unknown (code {code})")


async def get_real_weather_data(city_name: str, days: int = 1) -> Dict:
    """
    Gets real weather data for the specified city.

    Args:
        city_name: City name
        days: Number of forecast days

    Returns:
        Dictionary with weather data
    """
    # Получаем координаты города
    coordinates = await get_city_coordinates(city_name)
    if not coordinates:
        raise McpError(
            ErrorData(
                code=INVALID_PARAMS,
                message=f"Город '{city_name}' не найден"
            )
        )
    
    latitude, longitude = coordinates
    
    # Получаем данные о погоде
    weather_data = await get_weather_data(latitude, longitude, days)
    
    # Парсим текущую погоду
    current = weather_data["current"]
    current_time = datetime.fromisoformat(
        current["time"].replace("Z", "+00:00")
    )
    
    current_weather = {
        "temperature": round(current["temperature_2m"]),
        "condition": weather_code_to_description(current["weather_code"]),
        "humidity": current["relative_humidity_2m"],
        "wind_speed": round(current["wind_speed_10m"]),
        "pressure": round(current["surface_pressure"])
    }
    
    # Парсим прогноз
    daily = weather_data["daily"]
    forecast = []
    
    for i in range(len(daily["time"])):
        forecast_date = datetime.fromisoformat(daily["time"][i])
        
        forecast.append({
            "date": daily["time"][i],
            "weekday": forecast_date.strftime("%A"),
            "day_temp": round(daily["temperature_2m_max"][i]),
            "night_temp": round(daily["temperature_2m_min"][i]),
            "condition": weather_code_to_description(daily["weather_code"][i]),
            "wind_speed": round(daily["wind_speed_10m_max"][i]),
            "precipitation_chance": daily["precipitation_probability_max"][i] 
            if daily["precipitation_probability_max"][i] is not None else 0
        })
    
    return {
        "city": city_name.title(),
        "coordinates": {"latitude": latitude, "longitude": longitude},
        "current_time": current_time.strftime("%Y-%m-%d %H:%M UTC"),
        "current_weather": current_weather,
        "forecast": forecast
    }


@mcp.tool()
async def get_today_weather(city: str) -> str:
    """
    Gets real weather data for the specified city.

    Args:
        city_name: City name
        days: Number of forecast days

    Returns:
        Dictionary with weather data
    """
    try:
        if not city or not city.strip():
            raise McpError(
                ErrorData(
                    code=INVALID_PARAMS,
                    message="The city name cannot be empty"
                )
            )
        
        weather_data = await get_real_weather_data(city.strip(), 1)
        current = weather_data["current_weather"]
        today_forecast = weather_data["forecast"][0]
        coords = weather_data["coordinates"]
        
        result = f"""🌤️ Weather in the city today {weather_data['city']}

📍 Coordinates: {coords['latitude']:.2f}, {coords['longitude']:.2f}
🕒 Time: {weather_data['current_time']}

🌡️ Now: {current['temperature']}°C
☁️ Conditions: {current['condition']}
💧 Humidity: {current['humidity']}%
💨 Wind speed: {current['wind_speed']} м/с
📊 Pressure: {current['pressure']} гПа

📅 Forecast for today:
🌅 Maximum: {today_forecast['day_temp']}°C
🌙 Minimum: {today_forecast['night_temp']}°C
🌧️ Chance of precipitation: {today_forecast['precipitation_chance']}%

🔗 Данные предоставлены Open-Meteo API"""
        
        return result
        
    except Exception as e:
        if isinstance(e, McpError):
            raise
        raise McpError(
            ErrorData(
                code=INTERNAL_ERROR,
                message=f"Error retrieving weather data: {str(e)}"
            )
        ) from e


@mcp.tool()
async def get_weekly_forecast(city: str) -> str:
    """
    Gets the current weekly weather forecast for any city in the world.
    Data provided by the Open-Meteo API.

    Args:
        city: City name (in any language)

    Usage:
            get_weekly_forecast("London")
            get_weekly_forecast("Tokyo")
            get_weekly_forecast("Sydney")
            get_weekly_forecast("Berlin")
    """
    try:
        if not city or not city.strip():
            raise McpError(
                ErrorData(
                    code=INVALID_PARAMS,
                    message="The city name cannot be empty"
                )
            )
        
        weather_data = await get_real_weather_data(city.strip(), 7)
        coords = weather_data["coordinates"]
        
        city_name = weather_data['city']
        lat, lon = coords['latitude'], coords['longitude']
        result = f"""📅 Weekly weather forecast for the city {city_name}

📍 Coordinates: {lat:.2f}, {lon:.2f}
🕒 Updated: {weather_data['current_time']}

📊 Weekly forecast:
"""
        
        for day in weather_data['forecast']:
            weekday_ru = {
                'Monday': 'Monday',
                'Tuesday': 'Tuesday', 
                'Wednesday': 'Wednesday',
                'Thursday': 'Thursday',
                'Friday': 'Friday',
                'Saturday': 'Saturday',
                'Sunday': 'Sunday'
            }.get(day['weekday'], day['weekday'])
            
            result += f"""
📆 {day['date']} ({weekday_ru})
   🌅 Макс: {day['day_temp']}°C | 🌙 Мин: {day['night_temp']}°C
   ☁️ {day['condition']} | 💨 {day['wind_speed']} м/с
   🌧️ Chance of precipitation: {day['precipitation_chance']}%"""
        
        result += "\n\n🔗 Data provided by Open-Meteo API"
        
        return result
        
    except Exception as e:
        if isinstance(e, McpError):
            raise
        raise McpError(
            ErrorData(
                code=INTERNAL_ERROR,
                message=f"Error retrieving weather forecast: {str(e)}"
            )
        ) from e


# Настройка SSE транспорта
sse = SseServerTransport("/messages/")


async def handle_sse(request: Request):
    """SSE connection handler"""
    _server = mcp._mcp_server
    async with sse.connect_sse(
        request.scope,
        request.receive,
        request._send,
    ) as (reader, writer):
        await _server.run(
            reader, 
            writer, 
            _server.create_initialization_options()
        )


# Создание Starlette приложения
app = Starlette(
    debug=True,
    routes=[
        Route("/sse", endpoint=handle_sse),
        Mount("/messages/", app=sse.handle_post_message),
    ],
)

if __name__ == "__main__":
    print("🌤️ Running an MCP weather server with the Open-Meteo API...")
    print("📡 The server will be available at: http://localhost:8001")
    print("🔗 SSE endpoint: http://localhost:8001/sse")
    print("📧 Messages endpoint: http://localhost:8001/messages/")
    print("🛠️ Available tools:")
    print("   - get_today_weather(city) - current weather for any city")
    print("   - get_weekly_forecast(city) - forecast for the week")
    print("🌍 Data is provided by the Open-Meteo API (without an API key)")
    print("🆓 Cities from all over the world are supported!")
    
    uvicorn.run(app, host="0.0.0.0", port=8001) 