# Tools Reference

Memgram provides 110 MCP tools organized into twenty-five categories.

## Overview

| # | Tool | Category | Branch | Description |
|---|------|----------|--------|-------------|
| 1 | [`start_session`](sessions.md#start_session) | Session | yes | Begin a session, get resume context |
| 2 | [`end_session`](sessions.md#end_session) | Session | — | Close with structured summary |
| 3 | [`save_snapshot`](sessions.md#save_snapshot) | Session | — | Compaction checkpoint |
| 4 | [`get_resume_context`](sessions.md#get_resume_context) | Session | yes | Everything needed to resume |
| 5 | [`add_thought`](knowledge.md#add_thought) | Knowledge | yes | Store a thought/decision/observation |
| 6 | [`update_thought`](knowledge.md#update_thought) | Knowledge | yes | Modify an existing thought |
| 7 | [`add_rule`](knowledge.md#add_rule) | Knowledge | yes | Store a learned do/don't pattern |
| 8 | [`reinforce_rule`](knowledge.md#reinforce_rule) | Knowledge | — | Bump rule confidence |
| 9 | [`add_error_pattern`](knowledge.md#add_error_pattern) | Knowledge | yes | Log failure with cause and fix |
| 10 | [`link_items`](knowledge.md#link_items) | Knowledge | — | Connect items in the graph |
| 11 | [`search`](search.md#search) | Search | yes | FTS5 full-text search |
| 12 | [`search_by_embedding`](search.md#search_by_embedding) | Search | yes | Vector similarity search (RAG) |
| 13 | [`store_embedding`](search.md#store_embedding) | Search | — | Store a vector embedding |
| 14 | [`get_rules`](search.md#get_rules) | Search | yes | Get active rules for context |
| 15 | [`get_session_history`](search.md#get_session_history) | Search | yes | List past sessions |
| 16 | [`get_related`](search.md#get_related) | Search | — | Items linked via graph |
| 17 | [`get_project_summary`](projects.md#get_project_summary) | Projects | — | Get living project overview |
| 18 | [`update_project_summary`](projects.md#update_project_summary) | Projects | — | Update project overview |
| 19 | [`merge_projects`](projects.md#merge_projects) | Projects | — | Merge one project into another |
| 20 | [`create_group`](groups.md#create_group) | Groups | yes | Create a named cluster |
| 21 | [`add_to_group`](groups.md#add_to_group) | Groups | — | Add item to group |
| 22 | [`remove_from_group`](groups.md#remove_from_group) | Groups | — | Remove item from group |
| 23 | [`get_group`](groups.md#get_group) | Groups | yes | Get group with members |
| 24 | [`pin_item`](maintenance.md#pin_item) | Maintenance | — | Pin/unpin for resume context |
| 25 | [`archive_item`](maintenance.md#archive_item) | Maintenance | — | Archive (exclude from search) |
| 26 | [`get_health`](maintenance.md#get_health) | Maintenance | — | Database health/diagnostics |
| 27 | [`get_agent_stats`](maintenance.md#get_agent_stats) | Maintenance | — | Agent contribution statistics |
| 28 | [`create_plan`](plans.md#create_plan) | Plans | yes | Create a plan to track work |
| 29 | [`update_plan`](plans.md#update_plan) | Plans | — | Update plan fields |
| 30 | [`get_plan`](plans.md#get_plan) | Plans | — | Get plan with tasks and progress |
| 31 | [`list_plans`](plans.md#list_plans) | Plans | yes | List plans with filters |
| 32 | [`add_plan_task`](plans.md#add_plan_task) | Plans | — | Add a task to a plan |
| 33 | [`update_plan_task`](plans.md#update_plan_task) | Plans | — | Update a plan task |
| 34 | [`delete_plan_task`](plans.md#delete_plan_task) | Plans | — | Remove a task from a plan |
| 35 | [`create_spec`](specs.md#create_spec) | Specs | yes | Create a specification |
| 36 | [`update_spec`](specs.md#update_spec) | Specs | — | Update spec fields |
| 37 | [`get_spec`](specs.md#get_spec) | Specs | — | Get spec with linked features |
| 38 | [`list_specs`](specs.md#list_specs) | Specs | yes | List specs with filters |
| 39 | [`create_feature`](features.md#create_feature) | Features | yes | Define a feature |
| 40 | [`update_feature`](features.md#update_feature) | Features | — | Update feature fields |
| 41 | [`get_feature`](features.md#get_feature) | Features | — | Get feature with links |
| 42 | [`list_features`](features.md#list_features) | Features | yes | List features with filters |
| 43 | [`create_component`](components.md#create_component) | Components | yes | Define a system component |
| 44 | [`update_component`](components.md#update_component) | Components | — | Update component fields |
| 45 | [`get_component`](components.md#get_component) | Components | — | Get component with links |
| 46 | [`list_components`](components.md#list_components) | Components | yes | List components with filters |
| 47 | [`add_person`](people.md#add_person) | People | — | Add a person |
| 48 | [`update_person`](people.md#update_person) | People | — | Update person fields |
| 49 | [`get_person`](people.md#get_person) | People | — | Get person with ownership info |
| 50 | [`list_people`](people.md#list_people) | People | — | List people with filters |
| 51 | [`create_team`](teams.md#create_team) | Teams | yes | Create a team |
| 52 | [`update_team`](teams.md#update_team) | Teams | — | Update team fields |
| 53 | [`get_team`](teams.md#get_team) | Teams | — | Get team with members |
| 54 | [`list_teams`](teams.md#list_teams) | Teams | yes | List teams with filters |
| 55 | [`add_team_member`](teams.md#add_team_member) | Teams | — | Add person to team |
| 56 | [`remove_team_member`](teams.md#remove_team_member) | Teams | — | Remove person from team |
| 57 | [`get_instructions`](instructions.md#get_instructions) | Instructions | yes | Get active instructions for context |
| 58 | [`create_instruction`](instructions.md#create_instruction) | Instructions | yes | Create an instruction section |
| 59 | [`update_instruction`](instructions.md#update_instruction) | Instructions | yes | Update instruction fields |
| 60 | [`list_instruction_sections`](instructions.md#list_instruction_sections) | Instructions | yes | List section names/titles |
| 61 | [`add_attachment`](attachments.md#add_attachment) | Attachments | — | Attach URL/file to any entity |
| 62 | [`get_attachments`](attachments.md#get_attachments) | Attachments | — | Get attachments for an entity |
| 63 | [`update_attachment`](attachments.md#update_attachment) | Attachments | — | Update attachment fields |
| 64 | [`remove_attachment`](attachments.md#remove_attachment) | Attachments | — | Remove an attachment |
| 65 | [`create_ticket`](tickets.md#create_ticket) | Tickets | yes | Create a ticket with auto-number |
| 66 | [`update_ticket`](tickets.md#update_ticket) | Tickets | — | Update ticket fields |
| 67 | [`get_ticket`](tickets.md#get_ticket) | Tickets | — | Get ticket by ID or number |
| 68 | [`list_tickets`](tickets.md#list_tickets) | Tickets | yes | List tickets with filters |
| 69 | [`create_endpoint`](endpoints.md#create_endpoint) | Endpoints | yes | Define an API endpoint |
| 70 | [`update_endpoint`](endpoints.md#update_endpoint) | Endpoints | — | Update endpoint fields |
| 71 | [`get_endpoint`](endpoints.md#get_endpoint) | Endpoints | — | Get endpoint details |
| 72 | [`list_endpoints`](endpoints.md#list_endpoints) | Endpoints | yes | List endpoints with filters |
| 73 | [`create_credential`](credentials.md#create_credential) | Credentials | — | Register a secret reference |
| 74 | [`update_credential`](credentials.md#update_credential) | Credentials | — | Update credential fields |
| 75 | [`get_credential`](credentials.md#get_credential) | Credentials | — | Get credential details |
| 76 | [`list_credentials`](credentials.md#list_credentials) | Credentials | — | List credentials with filters |
| 77 | [`create_environment`](environments.md#create_environment) | Environments | — | Define an environment |
| 78 | [`update_environment`](environments.md#update_environment) | Environments | — | Update environment fields |
| 79 | [`get_environment`](environments.md#get_environment) | Environments | — | Get environment details |
| 80 | [`list_environments`](environments.md#list_environments) | Environments | — | List environments with filters |
| 81 | [`create_deployment`](deployments.md#create_deployment) | Deployments | yes | Record a deployment |
| 82 | [`update_deployment`](deployments.md#update_deployment) | Deployments | — | Update deployment fields |
| 83 | [`get_deployment`](deployments.md#get_deployment) | Deployments | — | Get deployment details |
| 84 | [`list_deployments`](deployments.md#list_deployments) | Deployments | yes | List deployments with filters |
| 85 | [`create_build`](builds.md#create_build) | Builds | yes | Record a CI/CD build |
| 86 | [`update_build`](builds.md#update_build) | Builds | — | Update build fields |
| 87 | [`get_build`](builds.md#get_build) | Builds | — | Get build details |
| 88 | [`list_builds`](builds.md#list_builds) | Builds | yes | List builds with filters |
| 89 | [`create_incident`](incidents.md#create_incident) | Incidents | — | Report an incident |
| 90 | [`update_incident`](incidents.md#update_incident) | Incidents | — | Update incident fields |
| 91 | [`get_incident`](incidents.md#get_incident) | Incidents | — | Get incident details |
| 92 | [`list_incidents`](incidents.md#list_incidents) | Incidents | — | List incidents with filters |
| 93 | [`create_dependency`](dependencies.md#create_dependency) | Dependencies | — | Track an external dependency |
| 94 | [`update_dependency`](dependencies.md#update_dependency) | Dependencies | — | Update dependency fields |
| 95 | [`get_dependency`](dependencies.md#get_dependency) | Dependencies | — | Get dependency details |
| 96 | [`list_dependencies`](dependencies.md#list_dependencies) | Dependencies | — | List dependencies with filters |
| 97 | [`create_runbook`](runbooks.md#create_runbook) | Runbooks | — | Create an operational runbook |
| 98 | [`update_runbook`](runbooks.md#update_runbook) | Runbooks | — | Update runbook fields |
| 99 | [`get_runbook`](runbooks.md#get_runbook) | Runbooks | — | Get runbook with steps |
| 100 | [`list_runbooks`](runbooks.md#list_runbooks) | Runbooks | — | List runbooks with filters |
| 101 | [`create_decision`](decisions.md#create_decision) | Decisions | yes | Create an ADR |
| 102 | [`update_decision`](decisions.md#update_decision) | Decisions | — | Update decision fields |
| 103 | [`get_decision`](decisions.md#get_decision) | Decisions | — | Get decision details |
| 104 | [`list_decisions`](decisions.md#list_decisions) | Decisions | yes | List decisions with filters |
| 105 | [`add_comment`](comments.md#add_comment) | Comments | — | Add comment to any entity |
| 106 | [`update_comment`](comments.md#update_comment) | Comments | — | Update comment content |
| 107 | [`get_comments`](comments.md#get_comments) | Comments | — | Get comments for an entity |
| 108 | [`delete_comment`](comments.md#delete_comment) | Comments | — | Delete a comment |
| 109 | [`log_audit`](audit.md#log_audit) | Audit | — | Log a change event |
| 110 | [`get_audit_log`](audit.md#get_audit_log) | Audit | — | Query the audit trail |

**Branch column**: "yes" means the tool accepts a `branch` parameter for scoped operations.

## Detailed Pages

- [Session Tools](sessions.md) — `start_session`, `end_session`, `save_snapshot`, `get_resume_context`
- [Knowledge Tools](knowledge.md) — `add_thought`, `update_thought`, `add_rule`, `reinforce_rule`, `add_error_pattern`, `link_items`
- [Search Tools](search.md) — `search`, `search_by_embedding`, `store_embedding`, `get_rules`, `get_session_history`, `get_related`
- [Project Tools](projects.md) — `get_project_summary`, `update_project_summary`, `merge_projects`
- [Group Tools](groups.md) — `create_group`, `add_to_group`, `remove_from_group`, `get_group`
- [Maintenance & Health](maintenance.md) — `pin_item`, `archive_item`, `get_health`, `get_agent_stats`
- [Plan Tools](plans.md) — `create_plan`, `update_plan`, `get_plan`, `list_plans`, `add_plan_task`, `update_plan_task`, `delete_plan_task`
- [Spec Tools](specs.md) — `create_spec`, `update_spec`, `get_spec`, `list_specs`
- [Feature Tools](features.md) — `create_feature`, `update_feature`, `get_feature`, `list_features`
- [Component Tools](components.md) — `create_component`, `update_component`, `get_component`, `list_components`
- [People Tools](people.md) — `add_person`, `update_person`, `get_person`, `list_people`
- [Team Tools](teams.md) — `create_team`, `update_team`, `get_team`, `list_teams`, `add_team_member`, `remove_team_member`
- [Instruction Tools](instructions.md) — `get_instructions`, `create_instruction`, `update_instruction`, `list_instruction_sections`
- [Attachment Tools](attachments.md) — `add_attachment`, `get_attachments`, `update_attachment`, `remove_attachment`
- [Ticket Tools](tickets.md) — `create_ticket`, `update_ticket`, `get_ticket`, `list_tickets`
- [Endpoint Tools](endpoints.md) — `create_endpoint`, `update_endpoint`, `get_endpoint`, `list_endpoints`
- [Credential Tools](credentials.md) — `create_credential`, `update_credential`, `get_credential`, `list_credentials`
- [Environment Tools](environments.md) — `create_environment`, `update_environment`, `get_environment`, `list_environments`
- [Deployment Tools](deployments.md) — `create_deployment`, `update_deployment`, `get_deployment`, `list_deployments`
- [Build Tools](builds.md) — `create_build`, `update_build`, `get_build`, `list_builds`
- [Incident Tools](incidents.md) — `create_incident`, `update_incident`, `get_incident`, `list_incidents`
- [Dependency Tools](dependencies.md) — `create_dependency`, `update_dependency`, `get_dependency`, `list_dependencies`
- [Runbook Tools](runbooks.md) — `create_runbook`, `update_runbook`, `get_runbook`, `list_runbooks`
- [Decision Tools](decisions.md) — `create_decision`, `update_decision`, `get_decision`, `list_decisions`
- [Comment Tools](comments.md) — `add_comment`, `update_comment`, `get_comments`, `delete_comment`
- [Audit Tools](audit.md) — `log_audit`, `get_audit_log`
