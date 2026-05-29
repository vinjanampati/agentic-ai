package com.example.demo.controller;

import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/weather")
public class WeatherController {

    // Mock weather data — in production this would call a real weather API
    private static final Map<String, Map<String, Object>> WEATHER_DB = Map.of(
        "london",   Map.of("city", "London",   "tempC", 14, "condition", "Cloudy",        "humidity", 75, "windKph", 18),
        "new york", Map.of("city", "New York", "tempC", 23, "condition", "Sunny",         "humidity", 55, "windKph", 12),
        "tokyo",    Map.of("city", "Tokyo",    "tempC", 27, "condition", "Partly Cloudy", "humidity", 80, "windKph", 8),
        "sydney",   Map.of("city", "Sydney",   "tempC", 17, "condition", "Rainy",         "humidity", 88, "windKph", 22),
        "paris",    Map.of("city", "Paris",    "tempC", 19, "condition", "Clear",         "humidity", 62, "windKph", 10),
        "berlin",   Map.of("city", "Berlin",   "tempC", 11, "condition", "Overcast",      "humidity", 70, "windKph", 15)
    );

    @GetMapping("/{city}")
    public Map<String, Object> getWeather(@PathVariable String city) {
        Map<String, Object> data = WEATHER_DB.get(city.toLowerCase());
        if (data != null) {
            return data;
        }
        // Return a plausible default for unknown cities
        return Map.of("city", city, "tempC", 20, "condition", "Unknown", "humidity", 65, "windKph", 10,
                      "note", "City not in mock database — showing defaults");
    }
}
