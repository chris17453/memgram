# Audit Tools

Two tools for maintaining a full change history — track who changed what and when on any entity.

Audit log entries record creates, updates, deletes, and status changes with before/after values and actor attribution.

## `log_audit`

Record an audit-log entry for a change to any entity.

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `entity_id` | string | **yes** | — | ID of the entity that was changed |
| `entity_type` | string | **yes** | — | Type of entity (see supported types below) |
| `action` | string | **yes** | — | `created`, `updated`, `deleted`, or `status_changed` |
| `field_changed` | string | no | — | Name of the field that was modified (e.g. `status`, `content`) |
| `old_value` | string | no | — | Previous value of the field (before the change) |
| `new_value` | string | no | — | New value of the field (after the change) |
| `actor` | string | no | — | Who or what performed the change (username, agent, system) |
| `project` | string | no | — | Project scope |

### Supported Entity Types

`person`, `team`, `component`, `feature`, `spec`, `plan`, `thought`, `rule`, `error_pattern`, `ticket`, `endpoint`, `credential`, `environment`, `deployment`, `build`, `incident`, `dependency`, `runbook`, `decision`, `instruction`

### Example Request

```json
{
  "entity_id": "a1b2c3d4e5f6",
  "entity_type": "ticket",
  "action": "status_changed",
  "field_changed": "status",
  "old_value": "open",
  "new_value": "in_progress",
  "actor": "alice",
  "project": "myapp"
}
```

## `get_audit_log`

Query the audit log. All filters are optional — combine them to narrow results. Returns entries in reverse chronological order.

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `entity_id` | string | no | — | Filter by entity ID |
| `entity_type` | string | no | — | Filter by entity type (see supported types above) |
| `action` | string | no | — | `created`, `updated`, `deleted`, or `status_changed` |
| `actor` | string | no | — | Filter by who performed the change |
| `project` | string | no | — | Filter by project scope |
| `limit` | integer | no | `100` | Max entries to return |
