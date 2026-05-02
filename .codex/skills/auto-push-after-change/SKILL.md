---
name: auto-push-after-change
description: Automatically commit and push code changes after completing a coding task in this repository. Use when the user wants every completed code modification to be synced to the configured Git remote without a separate reminder, especially for requests like "改完直接推上去", "自动提交并推送", or "每次修改代码都更新仓库".
---

# Auto Push After Change

After completing the requested code changes, treat Git sync as part of the task instead of an optional follow-up.

## Workflow

1. Confirm the repository is initialized and `origin` is configured.
2. Review `git status --short` before committing.
3. Stage only the files relevant to the task unless the user explicitly wants everything.
4. If generated artifacts, caches, secrets, virtual environments, model weights, or local data appear in the diff, stop and either exclude them or update `.gitignore` first.
5. Create a normal commit with a concise message that reflects the actual change.
6. Push the current branch to the configured remote.
7. Report the commit hash and push result in the final response.

## Commit Rules

- Do not amend old commits unless the user explicitly asks.
- Do not force-push unless the user explicitly asks to overwrite remote history.
- Do not include unrelated local files just because they are present.
- Prefer focused commit messages such as `Fix RL training dataset selection` or `Rewrite root README`.

## Approval And Failure Handling

- If Git commands require sandbox or network approval, request it and continue the workflow once granted.
- If push fails because of authentication, branch protection, or remote divergence, tell the user the exact blocker and stop there.
- If the repository is not initialized, initialize it only when that matches the user request.

## Final Response

Always include:

- what changed
- the commit hash
- whether push succeeded
- any remaining blocker if push did not succeed
