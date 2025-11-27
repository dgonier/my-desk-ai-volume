# CLAUDE.md - Volume Repository Instructions

This is the core code repository for my-desk.ai, cloned onto the Modal volume at `/home/claude/my-desk-ai-volume/`.

## Critical Workflow: Always Commit and Push

**After every change to files in this repository, you MUST:**

1. Stage the changes: `git add -A`
2. Commit with a descriptive message: `git commit -m "description of change"`
3. Push to origin: `git push origin main`

This ensures code persists across container restarts. The volume may lose uncommitted changes.

### Example workflow:
```bash
cd /home/claude/my-desk-ai-volume
# ... make changes ...
git add -A
git commit -m "feat: add new tool to persona agent"
git push origin main
```

## Directory Structure

```
/home/claude/
├── my-desk-ai-volume/     # THIS REPO - core code (git tracked)
│   ├── packages/          # Python modules
│   │   ├── agents/        # AI agent implementations
│   │   ├── cognitive/     # Graph and memory systems
│   │   ├── comms/         # Communication (WhatsApp, voice)
│   │   ├── private_services/  # OAuth, Gmail, Contacts
│   │   ├── relationships/ # Relationship management
│   │   └── research/      # Research and discovery
│   └── config/            # Configuration files
│
└── [user files]           # NOT in git - user-specific data
    ├── documents/
    ├── projects/
    └── etc.
```

## What Goes in This Repo (Core)

- `packages/` - All Python modules that power the agent
- `config/` - Shared configuration templates
- Core improvements that benefit all users

## What Does NOT Go in This Repo

- User-specific documents and data
- OAuth tokens and credentials
- Personal notes and files
- Anything in `.gitignore`

## Future Multi-User Workflow

When we expand to multiple users:
1. Users push changes to their own branch (e.g., `user/dgonier`)
2. Changes are reviewed before merging to `main`
3. Each user's container pulls from their branch or main

For now, push directly to `main`.

## On Container Startup

The container should run:
```bash
cd /home/claude/my-desk-ai-volume && git pull origin main
```

This ensures the latest core code is always available.
