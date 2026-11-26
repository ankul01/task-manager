# Agent Rules — task-manager

## Secret & Credential Protection (MANDATORY)

- **NEVER** read, open, print, log, or reference the contents of any of these files:
  - `.env`, `.env.local`, `.env.*.local`, `.env.production`, `.env.development`
  - Any file whose name contains `secret`, `password`, `credentials`, `token`, or `key`
  - `~/.ssh/*`, `~/.aws/credentials`, `~/.config/gh/hosts.yml`, `~/.netrc`
  - macOS Keychain files (`~/Library/Keychains/`)
- If a task requires knowing the **value** of an environment variable, ask the user to paste only the specific value in chat — never read the file yourself.
- If you accidentally read a secret value from a file, do **not** echo, log, or repeat it.

## Workspace Boundary

- This workspace is `task-manager` only. GitHub workflow `.yml` files and scripts are **read-only** reference — never modify them unless the user explicitly instructs it in that specific task prompt.
