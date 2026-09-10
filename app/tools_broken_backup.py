import inspect
import re

from datetime import datetime

import httpx

from app.config import (
    TAVILY_API_KEY
)

from app.http_retry import (
    request_with_retry
)

from app.errors import (
    ErrorCode,
    make_error_result,
    normalize_tool_error
)


# ---------------------------------
# EXTERNAL API URLS
# ---------------------------------

GEOCODING_URL = (
    "https://geocoding-api.open-meteo.com/v1/search"
)

WEATHER_URL = (
    "https://api.open-meteo.com/v1/forecast"
)

TAVILY_SEARCH_URL = (
    "https://api.tavily.com/search"
)


# ---------------------------------
# WEATHER CODE MAP
# ---------------------------------

WEATHER_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snowfall",
    73: "Moderate snowfall",
    75: "Heavy snowfall",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


# ---------------------------------
# CALCULATOR
# ---------------------------------

def calculator(
    operation: str,
    a,
    b
):

    try:
        a = float(a)
        b = float(b)

    except (
        TypeError,
        ValueError
    ):

        return {
            "error": (
                "Calculator values must "
                "be valid numbers."
            )
        }

    operation = str(
        operation
    ).lower().strip()

    if operation == "add":

        result = a + b

    elif operation == "subtract":

        result = a - b

    elif operation == "multiply":

        result = a * b

    elif operation == "divide":

        if b == 0:

            return {
                "error": (
                    "Division by zero "
                    "is not allowed."
                )
            }

        result = a / b

    else:

        return {
            "error": (
                f"Unsupported calculator "
                f"operation: {operation}"
            )
        }

    if result.is_integer():

        return int(
            result
        )

    return result


# ---------------------------------
# CURRENT DATE / TIME
# ---------------------------------

def get_current_datetime():

    now = datetime.now(
    ).astimezone()

    return {
        "date": now.strftime(
            "%Y-%m-%d"
        ),
        "time": now.strftime(
            "%H:%M:%S"
        ),
        "day": now.strftime(
            "%A"
        ),
        "timezone": str(
            now.tzinfo
        )
    }


# ---------------------------------
# WEATHER
# ---------------------------------

async def get_weather(
    city: str
):

    city = city.strip()

    if not city:

        return {
            "error": (
                "City cannot be empty."
            )
        }

    timeout = httpx.Timeout(
        connect=10.0,
        read=30.0,
        write=15.0,
        pool=10.0
    )

    try:

        async with httpx.AsyncClient(
            timeout=timeout
        ) as client:

            # ---------------------------------
            # GEOCODING
            # ---------------------------------

            geo_params = {
                "name": city,
                "count": 1,
                "language": "en",
                "format": "json"
            }

            geo_response = (
                await request_with_retry(
                    client=client,
                    method="GET",
                    url=GEOCODING_URL,
                    service_name=(
                        "open_meteo_geocoding"
                    ),
                    max_attempts=3,
                    base_delay=0.5,
                    max_delay=2.0,
                    params=geo_params
                )
            )

            geo_data = (
                geo_response.json()
            )

            geo_results = (
                geo_data.get(
                    "results",
                    []
                )
            )

            if not geo_results:

                return {
                    "error": (
                        f"Could not find "
                        f"location: {city}"
                    )
                }

            location = geo_results[0]

            latitude = location.get(
                "latitude"
            )

            longitude = location.get(
                "longitude"
            )

            resolved_city = (
                location.get(
                    "name",
                    city
                )
            )

            country = location.get(
                "country",
                ""
            )

            # ---------------------------------
            # WEATHER REQUEST
            # ---------------------------------

            weather_params = {
                "latitude": latitude,
                "longitude": longitude,
                "current": (
                    "temperature_2m,"
                    "apparent_temperature,"
                    "relative_humidity_2m,"
                    "precipitation,"
                    "weather_code,"
                    "wind_speed_10m"
                ),
                "timezone": "auto",
                "forecast_days": 1
            }

            weather_response = (
                await request_with_retry(
                    client=client,
                    method="GET",
                    url=WEATHER_URL,
                    service_name=(
                        "open_meteo_weather"
                    ),
                    max_attempts=3,
                    base_delay=0.5,
                    max_delay=2.0,
                    params=weather_params
                )
            )

            weather_data = (
                weather_response.json()
            )

            current = (
                weather_data.get(
                    "current",
                    {}
                )
            )

            weather_code = current.get(
                "weather_code"
            )

            condition = (
                WEATHER_CODES.get(
                    weather_code,
                    "Unknown"
                )
            )

            return {
                "city": resolved_city,
                "country": country,
                "temperature_c": (
                    current.get(
                        "temperature_2m"
                    )
                ),
                "feels_like_c": (
                    current.get(
                        "apparent_temperature"
                    )
                ),
                "humidity_percent": (
                    current.get(
                        "relative_humidity_2m"
                    )
                ),
                "precipitation_mm": (
                    current.get(
                        "precipitation"
                    )
                ),
                "wind_speed_kmh": (
                    current.get(
                        "wind_speed_10m"
                    )
                ),
                "condition": condition,
                "observed_at": (
                    current.get(
                        "time"
                    )
                )
            }

    except httpx.TimeoutException:

        return {
            "error": (
                "Weather service timed out."
            )
        }

    except httpx.HTTPStatusError as e:

        return {
            "error": (
                "Weather service returned "
                f"HTTP "
                f"{e.response.status_code}."
            )
        }

    except httpx.RequestError:

        return {
            "error": (
                "Could not connect to "
                "the weather service."
            )
        }

    except Exception as e:

        return {
            "error": (
                "Unexpected weather error: "
                f"{str(e)}"
            )
        }


# ---------------------------------
# WEB SEARCH
# ---------------------------------

async def web_search(
    query: str
):

    if not TAVILY_API_KEY:

        return {
            "error": (
                "Web search API key "
                "is not configured."
            )
        }

    query = query.strip()

    if not query:

        return {
            "error": (
                "Search query cannot "
                "be empty."
            )
        }

    timeout = httpx.Timeout(
        connect=10.0,
        read=30.0,
        write=15.0,
        pool=10.0
    )

    headers = {
        "Authorization": (
            f"Bearer {TAVILY_API_KEY}"
        ),
        "Content-Type": (
            "application/json"
        )
    }

    payload = {
        "query": query,
        "topic": "general",
        "search_depth": "basic",
        "max_results": 3,
        "include_answer": False,
        "include_raw_content": False,
        "include_images": False
    }

    try:

        async with httpx.AsyncClient(
            timeout=timeout
        ) as client:

            response = (
                await request_with_retry(
                    client=client,
                    method="POST",
                    url=TAVILY_SEARCH_URL,
                    service_name="tavily",
                    max_attempts=3,
                    base_delay=0.5,
                    max_delay=2.0,
                    headers=headers,
                    json=payload
                )
            )

            data = response.json()

        results = []

        for item in data.get(
            "results",
            []
        ):

            content = item.get(
                "content",
                ""
            ).strip()

            if len(content) > 700:

                content = (
                    content[:700]
                    + "..."
                )

            results.append({
                "title": item.get(
                    "title",
                    ""
                ),
                "url": item.get(
                    "url",
                    ""
                ),
                "snippet": content
            })

        if not results:

            return {
                "query": query,
                "results": [],
                "message": (
                    "No useful web results "
                    "were found."
                )
            }

        return {
            "query": query,
            "results": results
        }

    except httpx.TimeoutException:

        return {
            "error": (
                "Web search service "
                "timed out."
            )
        }

    except httpx.HTTPStatusError as e:

        return {
            "error": (
                "Web search API returned "
                f"HTTP "
                f"{e.response.status_code}."
            )
        }

    except httpx.RequestError:

        return {
            "error": (
                "Could not connect to "
                "web search service."
            )
        }

    except Exception as e:

        return {
            "error": (
                "Unexpected web search "
                f"error: {str(e)}"
            )
        }


# ---------------------------------
# TOOL SCHEMAS
# ---------------------------------

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": (
                "Perform basic arithmetic "
                "calculations."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": [
                            "add",
                            "subtract",
                            "multiply",
                            "divide"
                        ]
                    },
                    "a": {
                        "type": "number"
                    },
                    "b": {
                        "type": "number"
                    }
                },
                "required": [
                    "operation",
                    "a",
                    "b"
                ]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": (
                "get_current_datetime"
            ),
            "description": (
                "Get the current local "
                "date, time, and day."
            ),
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": (
                "Get current weather "
                "conditions for a city."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": (
                            "City or location "
                            "to check."
                        )
                    }
                },
                "required": [
                    "city"
                ]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": (
                "Search the live web for "
                "current, recent, changing, "
                "or externally verifiable "
                "information. Use when the "
                "user explicitly asks to "
                "search online or needs "
                "up-to-date information."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "Clear search query."
                        )
                    }
                },
                "required": [
                    "query"
                ]
            }
        }
    }
]


# ---------------------------------
# GUARDRAILS
# ---------------------------------

def allow_calculator(
    user_message: str
) -> bool:

    message = user_message.lower()

    has_number = bool(
        re.search(
            r"\d",
            message
        )
    )

    math_terms = [
        "+",
        "-",
        "*",
        "/",
        "plus",
        "minus",
        "add",
        "added",
        "subtract",
        "multiply",
        "multiplied",
        "times",
        "divide",
        "divided",
        "calculate",
        "calculation"
    ]

    return (
        has_number
        and any(
            term in message
            for term in math_terms
        )
    )


def allow_datetime(
    user_message: str
) -> bool:

    message = user_message.lower()

    datetime_terms = [
        "current time",
        "time now",
        "what time",
        "current date",
        "date today",
        "today's date",
        "todays date",
        "what date",
        "current day",
        "what day",
        "day today"
    ]

    return any(
        term in message
        for term in datetime_terms
    )


def allow_weather(
    user_message: str
) -> bool:

    message = user_message.lower()

    weather_terms = [
        "weather",
        "temperature",
        "humidity",
        "rain",
        "raining",
        "precipitation",
        "wind",
        "windy",
        "forecast"
    ]

    return any(
        term in message
        for term in weather_terms
    )


def allow_web_search(
    user_message: str
) -> bool:

    message = user_message.lower()

    explicit_search_terms = [
        "search the web",
        "search online",
        "web search",
        "look online",
        "look up online",
        "find online",
        "search for"
    ]

    freshness_terms = [
        "latest",
        "recent",
        "today",
        "today's",
        "yesterday",
        "this week",
        "this month",
        "current news",
        "latest news",
        "breaking news",
        "up to date",
        "up-to-date",
        "newest",
        "recently"
    ]

    changing_information_terms = [
        "current ceo",
        "current president",
        "current price",
        "latest version",
        "latest release",
        "latest update",
        "latest score",
        "latest results"
    ]

    return (
        any(
            term in message
            for term in explicit_search_terms
        )
        or
        any(
            term in message
            for term in freshness_terms
        )
        or
        any(
            term in message
            for term
            in changing_information_terms
        )
    )


# ---------------------------------
# GUARDRAIL REGISTRY
# ---------------------------------

TOOL_GUARDRAILS = {
    "calculator": allow_calculator,
    "get_current_datetime": (
        allow_datetime
    ),
    "get_weather": allow_weather,
    "web_search": allow_web_search,
}


def is_tool_allowed(
    tool_name: str,
    user_message: str
) -> bool:

    validator = (
        TOOL_GUARDRAILS.get(
            tool_name
        )
    )

    if validator is None:

        return False

    return validator(
        user_message
    )


# ---------------------------------
# TOOL REGISTRY
# ---------------------------------

TOOL_REGISTRY = {
    "calculator": calculator,
    "get_current_datetime": (
        get_current_datetime
    ),
    "get_weather": get_weather,
    "web_search": web_search,
}


# ---------------------------------
# GENERIC TOOL EXECUTOR
# ---------------------------------

async def execute_tool(
    tool_name: str,
    arguments: dict
):

    tool_function = (
        TOOL_REGISTRY.get(
            tool_name
        )
    )

    # ---------------------------------
    # UNKNOWN TOOL
    # ---------------------------------

    if tool_function is None:

        return make_error_result(
            code=ErrorCode.UNKNOWN_TOOL,
            message=(
                f"Unknown tool: "
                f"{tool_name}"
            ),
            service=tool_name
        )

    try:

        result = tool_function(
            **arguments
        )

        if inspect.isawaitable(
            result
        ):

            result = await result

    # ---------------------------------
    # INVALID ARGUMENTS
    # ---------------------------------

    except TypeError:

        return make_error_result(
            code=ErrorCode.INVALID_INPUT,
            message=(
                "The tool received "
                "invalid arguments."
            ),
            service=tool_name
        )

    # ---------------------------------
    # UNEXPECTED TOOL FAILURE
    # ---------------------------------

    except Exception:

        return make_error_result(
            code=(
                ErrorCode.TOOL_EXECUTION_ERROR
            ),
            message=(
                "The tool could not "
                "complete the request."
            ),
            service=tool_name
        )

    # ---------------------------------
    # NORMALIZE EXISTING TOOL ERRORS
    # ---------------------------------

    if (
        isinstance(
            result,
            dict
        )
        and
        "error" in result
    ):

        return normalize_tool_error(
            tool_name=tool_name,
            message=str(
                result["error"]
            )
        )

    return result

    except TypeError as e:

        return {
            "error": (
                "Invalid tool arguments: "
                f"{str(e)}"
            )
        }

    except Exception as e:

        return {
            "error": (
                "Tool execution failed: "
                f"{str(e)}"
            )
        }