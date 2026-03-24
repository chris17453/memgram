# Credential Tools

Four tools for managing credential references — never the actual secret values.

Track where credentials live (vault paths, env vars), who provides them, when they expire, and when they were last rotated. Maintain an inventory of credentials across projects without exposing sensitive data.

## `create_credential`

Store a reference to a secret or credential. Never stores the actual secret value.

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `name` | string | **yes** | — | Human-readable credential name |
| `project` | string | **yes** | — | Project tag |
| `type` | string | no | `"api_key"` | `api_key`, `token`, `password`, `certificate`, `ssh_key`, or `oauth` |
| `provider` | string | no | — | Service or provider (e.g. AWS, Stripe, GitHub) |
| `vault_path` | string | no | — | Path in secrets manager / vault |
| `env_var` | string | no | — | Environment variable name that holds the secret |
| `description` | string | no | — | What this credential is used for |
| `last_rotated` | string | no | — | ISO-8601 date when the credential was last rotated |
| `expires_at` | string | no | — | ISO-8601 date when the credential expires |
| `tags` | string[] | no | — | Tags |

### Example Request

```json
{
  "name": "Stripe API Key",
  "project": "myapp",
  "type": "api_key",
  "provider": "Stripe",
  "vault_path": "secret/myapp/stripe-api-key",
  "env_var": "STRIPE_API_KEY",
  "description": "Production Stripe API key for payment processing",
  "tags": ["payments", "production"]
}
```

## `update_credential`

Update a credential reference — name, type, provider, vault path, env var, rotation/expiry dates, tags.

### Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `credential_id` | string | **yes** | Credential ID to update |
| `name` | string | no | Credential name |
| `project` | string | no | Project tag |
| `type` | string | no | `api_key`, `token`, `password`, `certificate`, `ssh_key`, or `oauth` |
| `provider` | string | no | Provider |
| `vault_path` | string | no | Vault path |
| `env_var` | string | no | Environment variable name |
| `description` | string | no | Description |
| `last_rotated` | string | no | Last rotation date |
| `expires_at` | string | no | Expiry date |
| `tags` | string[] | no | Tags |

Only provided fields are updated.

## `get_credential`

Get a credential reference and its metadata.

### Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `credential_id` | string | **yes** | Credential ID |

## `list_credentials`

List credential references filtered by project, type, or provider.

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `project` | string | no | — | Filter by project |
| `type` | string | no | — | `api_key`, `token`, `password`, `certificate`, `ssh_key`, or `oauth` |
| `provider` | string | no | — | Filter by provider |
| `limit` | integer | no | `50` | Max results |
