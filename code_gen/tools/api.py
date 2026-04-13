"""
API calling tools for external services
Inspired by PraisonAI's API tools
"""
import json
from typing import Any, Dict, Optional
from urllib.parse import urljoin

import httpx

from code_gen.tools.base import Tool, ToolResult


class APICallTool(Tool):
    """Make HTTP API calls to external services"""
    
    name = "api_call"
    description = "Make HTTP requests to external APIs. Supports GET, POST, PUT, DELETE methods with custom headers and body."
    input_schema = {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "The API endpoint URL",
            },
            "method": {
                "type": "string",
                "description": "HTTP method (GET, POST, PUT, DELETE, PATCH)",
                "default": "GET",
            },
            "headers": {
                "type": "object",
                "description": "Custom HTTP headers",
                "default": {},
            },
            "body": {
                "type": "object",
                "description": "Request body for POST/PUT/PATCH (will be JSON encoded)",
            },
            "params": {
                "type": "object",
                "description": "Query parameters",
                "default": {},
            },
            "timeout": {
                "type": "integer",
                "description": "Request timeout in seconds",
                "default": 30,
            },
        },
        "required": ["url"],
    }
    
    async def execute(
        self,
        url: str,
        method: str = "GET",
        headers: Dict = None,
        body: Dict = None,
        params: Dict = None,
        timeout: int = 30
    ) -> ToolResult:
        try:
            headers = headers or {}
            params = params or {}
            
            # Set default content type for requests with body
            if body and "Content-Type" not in headers:
                headers["Content-Type"] = "application/json"
            
            async with httpx.AsyncClient(timeout=float(timeout)) as client:
                method = method.upper()
                
                if method == "GET":
                    response = await client.get(url, headers=headers, params=params)
                elif method == "POST":
                    response = await client.post(url, headers=headers, json=body, params=params)
                elif method == "PUT":
                    response = await client.put(url, headers=headers, json=body, params=params)
                elif method == "DELETE":
                    response = await client.delete(url, headers=headers, params=params)
                elif method == "PATCH":
                    response = await client.patch(url, headers=headers, json=body, params=params)
                else:
                    return ToolResult(
                        success=False,
                        content="",
                        error=f"Unsupported HTTP method: {method}"
                    )
                
                # Try to parse as JSON
                try:
                    data = response.json()
                    content = json.dumps(data, indent=2, ensure_ascii=False)
                except:
                    content = response.text
                
                result_data = {
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "url": str(response.url),
                }
                
                if response.status_code < 400:
                    return ToolResult(
                        success=True,
                        content=f"Status: {response.status_code}\n\n{content[:3000]}",
                        data=result_data
                    )
                else:
                    return ToolResult(
                        success=False,
                        content=f"Status: {response.status_code}\n\n{content[:3000]}",
                        error=f"HTTP {response.status_code}: {response.reason_phrase}",
                        data=result_data
                    )
                    
        except httpx.TimeoutException:
            return ToolResult(
                success=False,
                content="",
                error=f"Request timed out after {timeout} seconds"
            )
        except Exception as e:
            return ToolResult(
                success=False,
                content="",
                error=f"API call failed: {str(e)}"
            )


class WeatherTool(Tool):
    """Get weather information (using Open-Meteo free API)"""
    
    name = "weather"
    description = "Get current weather and forecast for a location. Uses Open-Meteo API (no API key required)."
    input_schema = {
        "type": "object",
        "properties": {
            "location": {
                "type": "string",
                "description": "City name or coordinates (e.g., 'London' or '51.5074,-0.1278')",
            },
            "days": {
                "type": "integer",
                "description": "Number of forecast days (1-7)",
                "default": 1,
            },
        },
        "required": ["location"],
    }
    
    async def execute(self, location: str, days: int = 1) -> ToolResult:
        try:
            # First, geocode the location
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Geocoding API
                geo_url = f"https://geocoding-api.open-meteo.com/v1/search"
                geo_params = {
                    "name": location,
                    "count": 1,
                    "language": "en",
                    "format": "json"
                }
                
                geo_response = await client.get(geo_url, params=geo_params)
                geo_data = geo_response.json()
                
                if not geo_data.get("results"):
                    return ToolResult(
                        success=False,
                        content="",
                        error=f"Location not found: {location}"
                    )
                
                result = geo_data["results"][0]
                lat = result["latitude"]
                lon = result["longitude"]
                city_name = result.get("name", location)
                country = result.get("country", "")
                
                # Weather API
                weather_url = "https://api.open-meteo.com/v1/forecast"
                weather_params = {
                    "latitude": lat,
                    "longitude": lon,
                    "current": ["temperature_2m", "relative_humidity_2m", "weather_code", "wind_speed_10m"],
                    "daily": ["temperature_2m_max", "temperature_2m_min", "weather_code"],
                    "timezone": "auto",
                    "forecast_days": min(max(days, 1), 7)
                }
                
                weather_response = await client.get(weather_url, params=weather_params)
                weather_data = weather_response.json()
                
                # Format weather code
                weather_codes = {
                    0: "Clear sky",
                    1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
                    45: "Fog", 48: "Depositing rime fog",
                    51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
                    61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
                    71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
                    95: "Thunderstorm", 96: "Thunderstorm with hail",
                }
                
                current = weather_data.get("current", {})
                daily = weather_data.get("daily", {})
                
                weather_code = current.get("weather_code", 0)
                weather_desc = weather_codes.get(weather_code, "Unknown")
                
                output = []
                output.append(f"🌤️ Weather for {city_name}, {country}")
                output.append(f"📍 Coordinates: {lat:.4f}, {lon:.4f}")
                output.append("")
                output.append("Current Conditions:")
                output.append(f"  🌡️ Temperature: {current.get('temperature_2m', 'N/A')}°C")
                output.append(f"  💧 Humidity: {current.get('relative_humidity_2m', 'N/A')}%")
                output.append(f"  🌪️ Wind Speed: {current.get('wind_speed_10m', 'N/A')} km/h")
                output.append(f"  ☁️ Condition: {weather_desc}")
                
                if days > 1 and daily:
                    output.append("")
                    output.append("Forecast:")
                    for i in range(min(days, len(daily.get("time", [])))):
                        date = daily["time"][i]
                        max_temp = daily["temperature_2m_max"][i]
                        min_temp = daily["temperature_2m_min"][i]
                        code = daily["weather_code"][i]
                        desc = weather_codes.get(code, "Unknown")
                        output.append(f"  {date}: {min_temp}°C - {max_temp}°C, {desc}")
                
                return ToolResult(
                    success=True,
                    content="\n".join(output),
                    data={
                        "location": {"name": city_name, "country": country, "lat": lat, "lon": lon},
                        "current": current,
                        "daily": daily
                    }
                )
                
        except Exception as e:
            return ToolResult(
                success=False,
                content="",
                error=f"Weather fetch failed: {str(e)}"
            )


class WikipediaTool(Tool):
    """Search Wikipedia for information"""
    
    name = "wikipedia"
    description = "Search Wikipedia for articles and summaries. Returns article summaries and related information."
    input_schema = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query or article title",
            },
            "language": {
                "type": "string",
                "description": "Wikipedia language code (en, zh, etc.)",
                "default": "en",
            },
            "sentences": {
                "type": "integer",
                "description": "Number of sentences in summary",
                "default": 5,
            },
        },
        "required": ["query"],
    }
    
    async def execute(self, query: str, language: str = "en", sentences: int = 5) -> ToolResult:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Search for articles
                search_url = f"https://{language}.wikipedia.org/w/api.php"
                search_params = {
                    "action": "query",
                    "list": "search",
                    "srsearch": query,
                    "format": "json",
                    "srlimit": 3
                }
                
                search_response = await client.get(search_url, params=search_params)
                search_data = search_response.json()
                
                if not search_data.get("query", {}).get("search"):
                    return ToolResult(
                        success=False,
                        content="",
                        error=f"No Wikipedia articles found for: {query}"
                    )
                
                results = []
                for item in search_data["query"]["search"][:2]:  # Get top 2 results
                    title = item["title"]
                    pageid = item["pageid"]
                    
                    # Get article extract
                    extract_params = {
                        "action": "query",
                        "pageids": pageid,
                        "prop": "extracts",
                        "exsentences": sentences,
                        "exintro": True,
                        "explaintext": True,
                        "format": "json"
                    }
                    
                    extract_response = await client.get(search_url, params=extract_params)
                    extract_data = extract_response.json()
                    
                    page = extract_data["query"]["pages"][str(pageid)]
                    extract = page.get("extract", "No summary available")
                    
                    url = f"https://{language}.wikipedia.org/wiki/{title.replace(' ', '_')}"
                    
                    results.append({
                        "title": title,
                        "url": url,
                        "summary": extract
                    })
                
                # Format output
                output = []
                for i, r in enumerate(results, 1):
                    output.append(f"\n{'='*50}")
                    output.append(f"{i}. {r['title']}")
                    output.append(f"   URL: {r['url']}")
                    output.append(f"{'='*50}")
                    output.append(r['summary'])
                
                return ToolResult(
                    success=True,
                    content=f"Wikipedia search results for '{query}':\n" + "\n".join(output),
                    data={"results": results, "query": query}
                )
                
        except Exception as e:
            return ToolResult(
                success=False,
                content="",
                error=f"Wikipedia search failed: {str(e)}"
            )
