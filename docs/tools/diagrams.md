# Diagrams

Store and export diagrams and visualizations as first-class entities. Supports mermaid syntax, Chart.js configs, D3 network graphs, service maps, and enhanced tables.

Diagrams export to markdown as fenced codeblocks and to HTML with rendered interactive visualizations.

## create_diagram

Create a diagram or visualization.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| title | string | Yes | | Diagram title |
| definition | string | Yes | | Diagram source (see formats below) |
| project | string | Yes | | Project name |
| diagram_type | string | No | mermaid | `mermaid`, `chart`, `network`, `servicemap`, `table` |
| description | string | No | | What this diagram shows |
| data_source | string | No | | Reserved for future auto-population |
| branch | string | No | | Branch name |
| session_id | string | No | | Associated session |
| tags | string[] | No | | Tags for categorization |

### Definition Formats

**mermaid** --- raw mermaid syntax:
```json
{
  "title": "Auth Flow",
  "definition": "graph TD\n  A[User] -->|login| B[Auth Service]\n  B -->|token| C[API Gateway]",
  "diagram_type": "mermaid",
  "project": "my-project"
}
```

**chart** --- Chart.js configuration JSON:
```json
{
  "title": "Build Success Rate",
  "diagram_type": "chart",
  "definition": "{\"type\":\"bar\",\"data\":{\"labels\":[\"Jan\",\"Feb\",\"Mar\"],\"datasets\":[{\"label\":\"Passed\",\"data\":[12,19,15]}]}}",
  "project": "my-project"
}
```

**network** --- nodes and edges JSON:
```json
{
  "title": "Service Dependencies",
  "diagram_type": "network",
  "definition": "{\"nodes\":[{\"id\":\"api\",\"label\":\"API\"},{\"id\":\"db\",\"label\":\"Database\"}],\"edges\":[{\"source\":\"api\",\"target\":\"db\"}]}",
  "project": "my-project"
}
```

**servicemap** --- topology layout (same format as network, renders with topology emphasis):
```json
{
  "title": "Production Topology",
  "diagram_type": "servicemap",
  "definition": "{\"nodes\":[{\"id\":\"lb\",\"label\":\"Load Balancer\"},{\"id\":\"app1\",\"label\":\"App Server 1\"}],\"edges\":[{\"source\":\"lb\",\"target\":\"app1\"}]}",
  "project": "my-project"
}
```

**table** --- sortable data table:
```json
{
  "title": "Dependency Versions",
  "diagram_type": "table",
  "definition": "{\"columns\":[\"Name\",\"Version\",\"Latest\"],\"rows\":[{\"Name\":\"flask\",\"Version\":\"3.0\",\"Latest\":\"3.1\"},{\"Name\":\"sqlalchemy\",\"Version\":\"2.0\",\"Latest\":\"2.0\"}]}",
  "project": "my-project"
}
```

## update_diagram

Update a diagram's fields.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| diagram_id | string | Yes | Diagram ID |
| title | string | No | New title |
| diagram_type | string | No | New type |
| definition | string | No | New definition |
| description | string | No | New description |
| tags | string[] | No | New tags |

## get_diagram

Get a diagram by ID.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| diagram_id | string | Yes | Diagram ID |

## list_diagrams

List diagrams with optional filters.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| project | string | No | | Filter by project |
| branch | string | No | | Filter by branch |
| diagram_type | string | No | | Filter by type |
| limit | integer | No | 50 | Max results |

## delete_diagram

Delete a diagram by ID.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| diagram_id | string | Yes | Diagram ID |

## Export Behavior

- **Markdown**: Mermaid diagrams export as ` ```mermaid ` fenced codeblocks (renders natively in GitHub, GitLab, Obsidian). Other types export as JSON codeblocks.
- **HTML**: Renders interactively using CDN-loaded libraries (mermaid.js, Chart.js, D3.js). Each diagram page includes a collapsible "View source" section.
