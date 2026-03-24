# Endpoint Tools

Four tools for managing API endpoint definitions — formal records of routes in your service.

Endpoints track method, path, auth requirements, rate limits, and request/response schemas. Link them to a project to keep your API surface documented and discoverable.

## `create_endpoint`

Create an API endpoint definition.

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `path` | string | **yes** | — | URL path (e.g. `/api/v1/users`) |
| `project` | string | **yes** | — | Project tag |
| `method` | string | no | `"GET"` | `GET`, `POST`, `PUT`, `PATCH`, `DELETE`, `HEAD`, or `OPTIONS` |
| `base_url` | string | no | — | Base URL of the API (e.g. `https://api.example.com`) |
| `description` | string | no | — | What this endpoint does |
| `auth_type` | string | no | — | `none`, `api_key`, `bearer`, `oauth`, or `basic` |
| `rate_limit` | string | no | — | Rate limit (e.g. `100/min`, `1000/hour`) |
| `request_schema` | string | no | — | JSON schema or description of the request body |
| `response_schema` | string | no | — | JSON schema or description of the response body |
| `status` | string | no | `"active"` | `active`, `deprecated`, or `planned` |
| `branch` | string | no | — | Git branch name |
| `tags` | string[] | no | — | Tags |

### Example Request

```json
{
  "path": "/api/v1/users",
  "project": "myapp",
  "method": "POST",
  "base_url": "https://api.example.com",
  "description": "Create a new user account",
  "auth_type": "bearer",
  "rate_limit": "100/min",
  "status": "active",
  "tags": ["users", "auth"]
}
```

## `update_endpoint`

Update an endpoint's fields — path, method, auth, rate limit, schemas, status, tags.

### Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `endpoint_id` | string | **yes** | Endpoint ID to update |
| `path` | string | no | URL path |
| `project` | string | no | Project tag |
| `method` | string | no | `GET`, `POST`, `PUT`, `PATCH`, `DELETE`, `HEAD`, or `OPTIONS` |
| `base_url` | string | no | Base URL |
| `description` | string | no | Description |
| `auth_type` | string | no | `none`, `api_key`, `bearer`, `oauth`, or `basic` |
| `rate_limit` | string | no | Rate limit |
| `request_schema` | string | no | Request body schema |
| `response_schema` | string | no | Response body schema |
| `status` | string | no | `active`, `deprecated`, or `planned` |
| `branch` | string | no | Branch name |
| `tags` | string[] | no | Tags |

Only provided fields are updated.

## `get_endpoint`

Get an API endpoint definition by ID.

### Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `endpoint_id` | string | **yes** | Endpoint ID |

## `list_endpoints`

List API endpoints filtered by project, branch, method, or status.

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `project` | string | no | — | Filter by project |
| `branch` | string | no | — | Filter by branch |
| `method` | string | no | — | `GET`, `POST`, `PUT`, `PATCH`, `DELETE`, `HEAD`, or `OPTIONS` |
| `status` | string | no | — | `active`, `deprecated`, or `planned` |
| `limit` | integer | no | `50` | Max results |
