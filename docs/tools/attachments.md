# Attachment Tools

Four tools for linking files, images, audio, documents, and URLs to any entity.

Attachments store **references** (URLs or relative file paths) — the actual files are NOT stored in the database. Use attachments for profile photos, architecture diagrams, audio recordings, documentation links, screenshots, etc.

## `add_attachment`

Attach a URL or local file path to any entity.

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `entity_id` | string | **yes** | — | ID of the entity to attach to |
| `entity_type` | string | **yes** | — | Type: `person`, `team`, `component`, `feature`, `spec`, `plan`, `thought`, `rule`, `error_pattern`, `project`, `instruction` |
| `url` | string | **yes** | — | URL or relative file path |
| `label` | string | no | `""` | Display label |
| `type` | string | no | `"link"` | `link`, `image`, `audio`, `video`, or `document` |
| `mime_type` | string | no | — | MIME type (e.g. `image/png`, `audio/mp3`) |
| `description` | string | no | `""` | Description of the attachment |
| `position` | integer | no | auto | Sort order |

### Supported Entity Types

Attachments can be added to any entity in memgram:

| Entity Type | Example Use |
|-------------|-------------|
| `person` | Profile photo, resume link |
| `team` | Team logo, wiki page |
| `component` | Architecture diagram, API docs |
| `feature` | Design mockup, demo video |
| `spec` | Requirements PDF, wireframes |
| `plan` | Gantt chart, status dashboard |
| `thought` | Screenshot of error, reference article |
| `rule` | Relevant documentation link |
| `project` | Project logo, onboarding doc |
| `instruction` | Reference material |

### Example: Person with Photo

```json
{
  "entity_id": "p1a2b3c4d5e6",
  "entity_type": "person",
  "url": "https://avatars.example.com/alice.jpg",
  "label": "Profile Photo",
  "type": "image",
  "mime_type": "image/jpeg"
}
```

### Example: Component with Diagram

```json
{
  "entity_id": "c1a2b3c4d5e6",
  "entity_type": "component",
  "url": "./docs/diagrams/auth-flow.png",
  "label": "Auth Flow Diagram",
  "type": "image",
  "description": "OAuth2 PKCE flow sequence diagram"
}
```

## `get_attachments`

Get all attachments for an entity, optionally filtered by type.

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `entity_id` | string | **yes** | — | ID of the entity |
| `entity_type` | string | no | — | Narrow by entity type |
| `type_filter` | string | no | — | `link`, `image`, `audio`, `video`, or `document` |

### Example Response

```json
{
  "count": 2,
  "attachments": [
    {
      "id": "a1b2c3d4e5f6",
      "entity_id": "p1a2b3c4d5e6",
      "entity_type": "person",
      "url": "https://avatars.example.com/alice.jpg",
      "label": "Profile Photo",
      "type": "image",
      "mime_type": "image/jpeg",
      "position": 0
    },
    {
      "id": "b2c3d4e5f6a1",
      "entity_id": "p1a2b3c4d5e6",
      "entity_type": "person",
      "url": "https://linkedin.com/in/alice",
      "label": "LinkedIn",
      "type": "link",
      "position": 1
    }
  ]
}
```

## `update_attachment`

Update an attachment's label, URL, type, MIME type, description, or position.

### Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `attachment_id` | string | **yes** | Attachment ID to update |
| `url` | string | no | New URL |
| `label` | string | no | New label |
| `type` | string | no | `link`, `image`, `audio`, `video`, or `document` |
| `mime_type` | string | no | New MIME type |
| `description` | string | no | New description |
| `position` | integer | no | New sort position |

Only provided fields are updated.

## `remove_attachment`

Remove an attachment by ID. This only removes the reference — the actual file/URL is unaffected.

### Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `attachment_id` | string | **yes** | Attachment ID to remove |
