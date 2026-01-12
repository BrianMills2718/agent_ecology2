# Pattern: Worktree Enforcement

## Problem

Multiple Claude Code instances working in the same directory causes:
- Uncommitted changes from one instance overwritten by another
- Branch switches mid-edit
- Merge conflicts from parallel uncommitted work
- Lost work when instances don't coordinate

Git worktrees solve this by giving each instance its own working directory, but there's no enforcement - instances can still accidentally edit the main directory.

## Solution

A PreToolUse hook that blocks Edit/Write operations when the target file is in the main repository directory (not a worktree).

## Files

| File | Purpose |
|------|---------|
| `.claude/settings.json` | Hook configuration |
| `.claude/hooks/protect-main.sh` | Script that checks file paths and blocks if in main |

## Setup

1. **Create hooks directory:**
   ```bash
   mkdir -p .claude/hooks
   ```

2. **Create the protection script** (`.claude/hooks/protect-main.sh`):
   ```bash
   #!/bin/bash
   MAIN_DIR="/path/to/your/main/repo"

   INPUT=$(cat)
   FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

   if [[ -z "$FILE_PATH" ]]; then
       exit 0
   fi

   if [[ "$FILE_PATH" == "$MAIN_DIR"/* ]]; then
       echo "BLOCKED: Cannot edit files in main directory" >&2
       echo "Create a worktree: git worktree add ../feature -b feature" >&2
       exit 2
   fi

   exit 0
   ```

3. **Make it executable:**
   ```bash
   chmod +x .claude/hooks/protect-main.sh
   ```

4. **Create settings.json** (`.claude/settings.json`):
   ```json
   {
     "hooks": {
       "PreToolUse": [
         {
           "matcher": "Edit|Write",
           "hooks": [
             {
               "type": "command",
               "command": "bash .claude/hooks/protect-main.sh",
               "timeout": 5000
             }
           ]
         }
       ]
     }
   }
   ```

5. **Update .gitignore** to track these files:
   ```
   # Track enforcement hooks
   !.claude/settings.json
   !.claude/hooks/
   ```

## Usage

Once installed, Claude Code instances in the main directory will see:

```
BLOCKED: Cannot edit files in main directory (/path/to/repo)

You're in the main directory. Create a worktree first:
  make worktree BRANCH=plan-NN-description

Or use an existing worktree:
  make worktree-list
```

The Edit/Write operation will be blocked, forcing the instance to use a worktree.

## Customization

**Change the main directory path:**
Edit `MAIN_DIR` in `protect-main.sh` to match your repository location.

**Allow exceptions:**
Add patterns to skip enforcement for specific files:
```bash
# Allow editing .claude files even in main
if [[ "$FILE_PATH" == *".claude/"* ]]; then
    exit 0
fi
```

**Different branch naming:**
Adjust the error message to match your branch naming convention.

## Limitations

- **Requires jq:** The script uses `jq` to parse JSON input
- **Path-based only:** Detects main vs worktree by path, not git internals
- **Per-project:** Must configure `MAIN_DIR` for each project
- **Read operations allowed:** Only blocks Edit/Write, not Read (intentional - reviewing main is fine)
- **Bash operations allowed:** Doesn't block shell commands (could add if needed)

## Related Patterns

- [Claim System](claim-system.md) - Coordinates which instance works on what
- [Git Hooks](git-hooks.md) - Pre-commit validation before pushing
- [PR Coordination](pr-coordination.md) - Tracks review requests across instances
