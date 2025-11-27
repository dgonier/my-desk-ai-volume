# my-desk-ai-volume

Persistent files for the my-desk.ai Modal volume. This repo is cloned onto the Modal volume at `/home/claude/` and can be updated via `git pull`.

## Structure

```
.
├── packages/           # Core Python modules
│   ├── agents/         # AI agent implementations
│   ├── cognitive/      # Cognitive graph and memory
│   ├── comms/          # Communication handlers
│   ├── private_services/ # Private API integrations
│   ├── relationships/  # Relationship management
│   └── research/       # Research and discovery
├── config/             # Configuration files
│   ├── claude-settings.json
│   └── srt-settings.json
└── .claude/            # Claude Code settings
```

## Usage

On the Modal container, this repo lives at `/home/claude/`. To update:

```bash
cd /home/claude
git pull origin main
```

## Volume Persistence

The Modal volume mounts at `/home/claude`. Changes made by Claude Code are persisted via git commits and pushes, ensuring code survives container restarts.
