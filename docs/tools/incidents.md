# Incident Tools

Four tools for managing incidents — tracking outages, bugs, and production issues.

Incidents have severity levels (p0--p4), status tracking through investigation to resolution, and support timelines, root-cause analysis, and post-mortems. Assign a lead to track who is driving the response.

## `create_incident`

Create an incident record.

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `title` | string | **yes** | — | Incident title |
| `project` | string | **yes** | — | Project tag |
| `severity` | string | no | `"p3"` | `p0`, `p1`, `p2`, `p3`, or `p4` |
| `status` | string | no | `"investigating"` | `investigating`, `identified`, `monitoring`, `resolved`, or `postmortem` |
| `description` | string | no | — | What happened and what is the impact |
| `root_cause` | string | no | — | Identified root cause of the incident |
| `resolution` | string | no | — | How the incident was resolved |
| `timeline` | object[] | no | — | Chronological list of events (each with `timestamp` and `description`) |
| `lead_id` | string | no | — | Person ID of the incident lead |
| `started_at` | string | no | — | When the incident started (ISO 8601) |
| `resolved_at` | string | no | — | When the incident was resolved (ISO 8601) |
| `tags` | string[] | no | — | Tags |

### Example Request

```json
{
  "title": "Database connection pool exhaustion",
  "project": "myapp",
  "severity": "p1",
  "status": "investigating",
  "description": "All database connections exhausted, API returning 503",
  "lead_id": "p1a2b3c4d5e6",
  "started_at": "2025-03-15T14:30:00Z",
  "tags": ["database", "outage"]
}
```

### Status Flow

```
investigating → identified → monitoring → resolved → postmortem
```

## `update_incident`

Update an incident's fields — severity, status, root cause, resolution, timeline, lead, tags.

### Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `incident_id` | string | **yes** | Incident ID to update |
| `title` | string | no | New title |
| `project` | string | no | Project tag |
| `severity` | string | no | `p0`, `p1`, `p2`, `p3`, or `p4` |
| `status` | string | no | `investigating`, `identified`, `monitoring`, `resolved`, or `postmortem` |
| `description` | string | no | Description |
| `root_cause` | string | no | Root cause |
| `resolution` | string | no | Resolution |
| `timeline` | object[] | no | Timeline events |
| `lead_id` | string | no | Incident lead |
| `started_at` | string | no | Start timestamp |
| `resolved_at` | string | no | Resolution timestamp |
| `tags` | string[] | no | Tags |

Only provided fields are updated.

## `get_incident`

Get an incident by ID with its full details, timeline, and linked entities.

### Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `incident_id` | string | **yes** | Incident ID |

## `list_incidents`

List incidents filtered by project, severity, status, or lead.

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `project` | string | no | — | Filter by project |
| `severity` | string | no | — | `p0`, `p1`, `p2`, `p3`, or `p4` |
| `status` | string | no | — | `investigating`, `identified`, `monitoring`, `resolved`, or `postmortem` |
| `lead_id` | string | no | — | Filter by incident lead |
| `limit` | integer | no | `50` | Max results |
