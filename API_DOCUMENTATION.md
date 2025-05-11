# Proletto API Documentation

## Overview

Proletto provides a RESTful API for accessing artist opportunity data and recommendations. The API is designed to be used by third-party applications and services that want to integrate with Proletto's opportunity database and recommendation engine.

## Base URL

- **Production**: `https://api.myproletto.com`
- **Development**: `http://localhost:5001`

## Authentication

All API endpoints require authentication using an API key. You can provide the API key in one of two ways:

1. As a query parameter: `?key=YOUR_API_KEY`
2. As a request header: `X-API-KEY: YOUR_API_KEY`

Contact Proletto support at support@myproletto.com to obtain an API key.

## API Documentation

Interactive API documentation is available through Swagger UI:

- **Production**: [https://api.myproletto.com/api/docs](https://api.myproletto.com/api/docs)
- **Development**: [http://localhost:5001/api/docs](http://localhost:5001/api/docs)

The Swagger UI provides:
- A list of all available endpoints
- Request parameters and their descriptions
- Response formats and examples
- The ability to test endpoints directly from the browser

## Available Endpoints

### 1. Health Check

- **Endpoint**: `/api/v2/health`
- **Method**: GET
- **Description**: Returns the current health status of the API
- **Authentication**: Required
- **Success Response**:
  ```json
  {
    "status": "ok",
    "api_version": "v2",
    "timestamp": "2025-05-06T21:49:25.123456Z",
    "server_time": "2025-05-06 21:49:25 UTC"
  }
  ```

### 2. API Statistics

- **Endpoint**: `/api/v2/stats`
- **Method**: GET
- **Description**: Returns high-level API usage statistics
- **Authentication**: Required
- **Success Response**:
  ```json
  {
    "api_version": "v2",
    "timestamp": "2025-05-06T21:49:25.123456Z",
    "stats": {
      "user_count": 3,
      "premium_users": 2,
      "opportunity_count": 2254,
      "scheduler_status": "running",
      "environments": {
        "web": true,
        "api": true,
        "scheduler": true,
        "database": true
      }
    }
  }
  ```

### 3. Opportunity Recommendations

- **Endpoint**: `/api/v2/recommendations`
- **Method**: GET
- **Description**: Returns personalized art opportunity recommendations for a user
- **Authentication**: Required
- **Parameters**:
  - `user_id` (required): ID of the user to get recommendations for
  - `limit` (optional): Maximum number of recommendations to return (default: 10, max: 50)
  - `offset` (optional): Number of recommendations to skip for pagination (default: 0)
- **Success Response**:
  ```json
  {
    "api_version": "v2",
    "timestamp": "2025-05-06T21:49:25.123456Z",
    "recommendations": [
      {
        "id": "123",
        "title": "Artist Residency Program",
        "url": "https://example.com/opportunity/123",
        "confidence": 0.92,
        "category": "residency",
        "deadline": "2025-06-15"
      }
    ],
    "user_id": 1,
    "count": 1,
    "pagination": {
      "limit": 10,
      "offset": 0,
      "next_offset": null,
      "has_more": false
    }
  }
  ```

## Error Handling

All API endpoints return a standardized error format:

```json
{
  "api_version": "v2",
  "timestamp": "2025-05-06T21:49:25.123456Z",
  "error": {
    "code": 400,
    "message": "Invalid parameter"
  }
}
```

Common HTTP status codes:

- `200`: Request successful
- `400`: Bad request (e.g., invalid parameters)
- `401`: Unauthorized (invalid or missing API key)
- `403`: Forbidden (insufficient permissions)
- `404`: Resource not found
- `500`: Server error

## Pagination

Endpoints that return collections support pagination using the `limit` and `offset` parameters:

- `limit`: Number of items to return (default varies by endpoint)
- `offset`: Number of items to skip

The response includes pagination metadata:

```json
"pagination": {
  "limit": 10,
  "offset": 0,
  "next_offset": 10, // null if no more results
  "has_more": true
}
```

## Rate Limiting

The API enforces rate limiting to ensure fair usage. Rate limits are based on the API key and vary depending on your subscription plan.

If you exceed the rate limit, you'll receive a `429 Too Many Requests` response.

## Support

For API support, contact:

- Email: support@myproletto.com
- Website: https://www.myproletto.com/api-support