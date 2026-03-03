# Name Normalization

Memgram normalizes `project`, `branch`, `keywords`, and group `name` values to ensure consistent matching regardless of formatting.

## Algorithm

The normalization function (`normalize_name` in `utils.py`):

1. Converts to lowercase
2. Strips all non-alphanumeric characters (hyphens, underscores, slashes, dots, spaces)

```python
def normalize_name(value: str) -> str:
    return re.sub(r'[^a-z0-9]', '', value.lower())
```

## Examples

| Input | Normalized |
|-------|-----------|
| `oxide-os` | `oxideos` |
| `oxide_os` | `oxideos` |
| `OxideOS` | `oxideos` |
| `feature/auth-flow` | `featureauthflow` |
| `Feature/Auth_Flow` | `featureauthflow` |
| `my-app` | `myapp` |
| `My App` | `myapp` |
| `fix/login-bug` | `fixloginbug` |

## Where Normalization Applies

Normalization happens in the **tool dispatch layer** (`tools/__init__.py`), which acts as a choke point for all incoming tool calls. The following fields are normalized before reaching business logic:

| Field | Normalized? | Applied In |
|-------|-------------|------------|
| `project` | Yes | All tools that accept `project` |
| `branch` | Yes | All tools that accept `branch` |
| `keywords` | Yes (each element) | `add_thought`, `add_rule`, `add_error_pattern`, `get_rules`, `search` |
| Group `name` | Yes | `create_group`, `get_group` |
| `agent_type` | No | Stored as-is |
| `summary` | No | Stored as-is (searchable via FTS) |

## Implications

- You don't need to pre-normalize values before calling tools — the dispatcher handles it
- `feature/auth`, `feature_auth`, and `FeatureAuth` all resolve to the same branch
- Keyword matching uses normalized comparison, so `["JWT", "auth"]` matches `["jwt", "auth"]`
- Group names are normalized, so `"Auth System"` and `"auth-system"` refer to the same group
