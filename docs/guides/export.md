# Export

Memgram supports three export formats: **markdown** (linked `.md` files), **web** (navigable HTML site), and **PDF** (dark-themed report). All produce human-readable output and support project filtering. Useful for auditing, sharing, or backing up your knowledge base.

## Markdown Export

```bash
# Default: exports to ./memgram-export/
memgram export

# Custom output directory
memgram export -o ./my-export

# Export only a specific project
memgram export --project myapp

# Custom database path
memgram --db-path /path/to/memgram.db export -o ./my-export
```

## Web Export

Export as a navigable Jekyll HTML website — GitHub Pages ready, no build step needed.

```bash
# Default: exports to ./memgram-web/
memgram export-web

# Custom output directory
memgram export-web -o ./my-site

# Export only a specific project
memgram export-web --project myapp
```

After export, browse locally:

```bash
python -m http.server -d memgram-web
# or just open memgram-web/index.html
```

## PDF Export

Export as a styled dark-themed PDF report with cover page, linked table of contents, summary tables, and full detail sections for every entity type.

```bash
# Default: exports to ./report.pdf
memgram export-pdf

# Custom output file
memgram export-pdf -o ./my-report.pdf

# Export only a specific project
memgram export-pdf --project myapp
```

The PDF includes:

- **Cover page** with entity count stats grid
- **Linked table of contents** that jumps to each section
- **Summary tables** for each entity type (sessions, thoughts, rules, errors, etc.)
- **Full detail sections** with complete content for every item — no truncation
- **Markdown rendering** — headers, bullet lists, bold, inline code, and numbered lists are properly formatted
- **Mermaid diagram rendering** — if `mmdc` ([mermaid-cli](https://github.com/mermaid-js/mermaid-cli)) is installed, diagrams render as images; otherwise the source is shown as formatted code
- **Dark theme** throughout with consistent styling

To get rendered diagram images in the PDF, install mermaid-cli:

```bash
npm install -g @mermaid-js/mermaid-cli
```

## Output Structure

```
memgram-export/
|-- index.md                     # Overview with stats, rules summary, recent sessions
|-- sessions/
|   \-- <session-slug>.md        # One file per session (with snapshots and summaries)
|-- thoughts/
|   \-- <thought-slug>.md        # One file per thought
|-- rules/
|   \-- <rule-slug>.md           # One file per rule
|-- errors/
|   \-- <error-slug>.md          # One file per error pattern
|-- groups/
|   \-- <group-slug>.md          # One file per group (with member links)
\-- projects/
    \-- <project-slug>.md        # Per-project view (rules, thoughts, errors, sessions)
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

## Filenames

- Slugs are lowercase, spaces become dashes, non-alphanumerics are stripped, and names are capped at 80 characters.
- Collisions are resolved with numeric suffixes (`-2`, `-3`, ...).
- Links inside files always point to the slugged filenames.

## Cross-Linking

All files use relative markdown links to connect to related items:

- Session files link to their snapshots inline
- Thought/rule/error files link back to their session
- Error patterns link to their prevention rule
- Group members link to their detail files
- Project pages link to all associated items

## Migrating Legacy Exports

If you have an older export with ID-based filenames, convert it in place:

```bash
memgram migrate-exports -i ./memgram-export
```

All filenames are rewritten to slugs and internal links are updated. Safe to re-run.

## File Count

The export creates 1 index file + 1 file per session, thought, rule, error pattern, group, and project. The total count is printed after export completes:

```
Exported 142 files to /home/user/memgram-export
```
