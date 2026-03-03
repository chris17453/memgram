# Markdown Export

The `memgram export` command dumps the entire database as a tree of linked markdown files. Useful for auditing, sharing, or backing up your knowledge base.

## Usage

```bash
# Default: exports to ./memgram-export/
memgram export

# Custom output directory
memgram export -o ./my-export

# Custom database path
memgram --db-path /path/to/memgram.db export -o ./my-export
```

## Output Structure

```
memgram-export/
|-- index.md               # Overview with stats, rules summary, recent sessions
|-- sessions/
|   \-- <id>.md            # One file per session (with snapshots and summaries)
|-- thoughts/
|   \-- <id>.md            # One file per thought
|-- rules/
|   \-- <id>.md            # One file per rule
|-- errors/
|   \-- <id>.md            # One file per error pattern
|-- groups/
|   \-- <id>.md            # One file per group (with member links)
\-- projects/
    \-- <project>.md       # Per-project view (rules, thoughts, errors, sessions)
```

## What Each File Contains

### `index.md`

- **Stats table**: counts of sessions, thoughts, rules, errors, groups, links, projects
- **Rules overview**: severity, type, summary, reinforcement count, project — sorted by pinned/severity
- **Recent sessions**: last 20 sessions with date, agent, model, project, goal, status
- **Projects list**: links to each project page

### `sessions/<id>.md`

- Session metadata table (ID, agent, model, project, branch, status, dates, compaction count)
- Session summary (if set)
- Structured session summary (outcome, decisions, files modified, unresolved items, next hints)
- Compaction snapshots (ordered by sequence number) with goal, progress, next steps, blockers

### `thoughts/<id>.md`

- Pin/archive badges
- Metadata table (ID, type, project, branch, created date, access count, keywords, files, session link)
- Full content

### `rules/<id>.md`

- Severity and type badges
- Pin/archive badges
- Metadata table (ID, reinforcement count, project, branch, condition, keywords, files, session link)
- Full content/details

### `errors/<id>.md`

- Metadata table (ID, project, branch, keywords, files, prevention rule link, session link)
- Error description, cause, and fix

### `groups/<id>.md`

- Description and metadata table (ID, project, branch, member count, last updated)
- Member list with type badges and links to member files

### `projects/<project>.md`

An aggregated view of everything in a project:

- Project summary (if exists): overview, tech stack, key patterns, active goals, stats
- All rules in the project (with severity/type badges and links)
- All thoughts (up to 50, with type badges and links)
- All error patterns (with links)
- All sessions (last 20, in table format)

## Cross-Linking

All files use relative markdown links to connect to related items:

- Session files link to their snapshots inline
- Thought/rule/error files link back to their session
- Error patterns link to their prevention rule
- Group members link to their detail files
- Project pages link to all associated items

## File Count

The export creates 1 index file + 1 file per session, thought, rule, error pattern, group, and project. The total count is printed after export completes:

```
Exported 142 files to /home/user/memgram-export
```
