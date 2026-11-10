# Private Markdown Vault

The API indexes Markdown files recursively. Suggested folders:

- `Projects/`: project briefs, architecture and decisions
- `Rules/`: durable instructions and operating constraints
- `Logs/`: execution logs (exclude secrets)
- `Daily/`: daily notes

Keep sensitive credentials out of this directory. Markdown files are indexed into the local SQLite FTS5 store when `POST /v1/memory/ingest-vault` is called.
