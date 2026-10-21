# Auth Module -- Stage 4 Compliance Changes

**Module:** auth
**Author:** Compliance Coder (Stage 4)
**Date:** 2026-02-07
**Scope:** P1 fixes from stage3-fixes.md (excluding P3-01 file length and P3-02 function length)

---

## Changes Made

### P1-07: CLI Exercises Same Code Paths (FIXED)

**File:** `src/cli/commands/auth_commands.py`

**Finding:** The `hash-password` and `verify-password` CLI commands bypassed `AuthService` by directly calling `do_hash_password()` and `do_verify_password()` from `password_handler`. This meant the password strength validation path (`VALIDATION_WEAK_PASSWORD` check in `AuthService.hash_password()`) was never exercised by the CLI.

**Fix:** Updated both commands to route through `AuthService` using the existing `_run_async()` bridge pattern:

**Before (hash-password):**
```python
@auth.command("hash-password")
@click.argument("password")
def hash_password(password: str) -> None:
    """Hash a password with bcrypt."""
    hashed = do_hash_password(password)
    console.print(f"[bold green]Hash:[/bold green] {hashed}")
```

**After (hash-password):**
```python
@auth.command("hash-password")
@click.argument("password")
def hash_password(password: str) -> None:
    """Hash a password with bcrypt (routes through AuthService for validation)."""

    async def _do(svc: AuthService) -> None:
        hashed = svc.hash_password(password)
        console.print(f"[bold green]Hash:[/bold green] {hashed}")

    _run_async(_do)
```

Same pattern applied to `verify-password` command.

**Additional changes in the same file:**
- Removed unused imports: `hash_password as do_hash_password` and `verify_password as do_verify_password` from `src.modules.auth.password_handler`.
- Updated module docstring to reflect that these commands now route through AuthService.
- Updated section comment from "Sync commands (no database required)" to "Password commands (route through AuthService for validation)".

**Behavioral impact:**
- `hash-password` now validates password strength (min length, complexity) before hashing, matching the primary presentation layer path.
- `verify-password` now calls `AuthService.verify_password()` for consistency, though the service method currently delegates directly to the utility function.
- Both commands now require a full application context (config, database), meaning they need a valid configuration file to run. This is a trade-off for ensuring CLI exercises the same code paths.

---

## Not Fixed (Out of Scope)

| Finding | Reason |
|---------|--------|
| P3-01: service.py file length (705 lines) | Excluded per instructions |
| P3-02: Function length violations (5 methods) | Excluded per instructions |
| P3-04: Magic numbers (255, *60) | Passed with minor note in stage3; no fix required |

---

## Verification

- `hash-password` CLI command now calls `AuthService.hash_password()` which includes `VALIDATION_WEAK_PASSWORD` check.
- `verify-password` CLI command now calls `AuthService.verify_password()`.
- No direct `password_handler` imports remain in `auth_commands.py`.
- No test files were modified.
