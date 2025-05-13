# API Reference

This document provides detailed information about the API endpoints, their parameters, and responses.

## Authentication

All endpoints require API key authentication via the `X-API-Key` header:

```http
X-API-Key: your-api-key-here
```

## Health Endpoints

### GET /health

Basic health check endpoint for monitoring.

**Response:**

```json
{
  "status": "ok"
}
```

### GET /ready

Readiness probe for the service.

**Response:**

```json
{
  "status": "ready"
}
```

### GET /metrics

Prometheus-compatible metrics endpoint.

**Response:**
Prometheus-formatted metrics data.

## Batch Operations

### POST /batch

Process a batch of operations.

**Request Body:**

```json
{
  "operations": [
    {
      "type": "string",
      "data": {
        "key": "value"
      }
    }
  ]
}
```

**Response:**

```json
{
  "status": "processing",
  "operations": 1
}
```

## Error Responses

All endpoints may return the following error responses:

### 400 Bad Request

```json
{
  "detail": "Invalid request parameters"
}
```

### 401 Unauthorized

```json
{
  "detail": "Invalid or missing API key"
}
```

### 500 Internal Server Error

```json
{
  "detail": "Internal server error"
}
```

## Rate Limiting

The API implements rate limiting to ensure fair usage:

- 100 requests per minute for standard endpoints
- 1000 requests per minute for health check endpoints

Rate limit headers are included in all responses:

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 99
X-RateLimit-Reset: 1619123456
```

## Best Practices

1. **Error Handling**

   - Always check for error responses
   - Implement exponential backoff for retries
   - Log failed requests for debugging

2. **Performance**

   - Use batch endpoints for multiple operations
   - Implement client-side caching where appropriate
   - Monitor rate limits to avoid throttling

3. **Security**
   - Never log or expose API keys
   - Use HTTPS for all requests
   - Rotate API keys regularly
