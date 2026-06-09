---
name: code-review
owner: engineering
maturity: stable
triggers: [review, pr, pull request, diff, code review]
---

# Code Review Skill

Review a PR or diff for correctness, style, security, and tests. **Output a verdict + a list of issues, each with a file:line citation.**

## When to use

- Trigger: user says "review", "PR", "diff", "code review", or `/review`
- Trigger: GitHub webhook on PR open/update (future)

## How

1. Get the diff (`git diff main...HEAD` or `gh pr diff <N>`)
2. For each hunk:
   - Read the change
   - Check: does it do what the PR description claims?
   - Check: are there tests? If logic changed, do they pass?
   - Check: any security implications? (auth, input validation, secrets)
   - Check: any breaking changes to public APIs?
3. Run the full test suite: `pytest tests/ -q`
4. Output a structured review

## Output shape

```markdown
## Review: [PR title or branch name]

**Verdict:** (approve / request-changes / needs-discussion)
**Summary:** (1-2 sentences)

### Issues

- **[severity]** file:line — [description]
- **[severity]** file:line — [description]

### Strengths
- [what the PR does well]

### Suggested changes
- [concrete edits, with line numbers]

### Test status
- [pass/fail counts, any skipped]
```

## Anti-patterns

- Don't approve without reading every hunk
- Don't request changes without a file:line citation
- Don't bikeshed style (that's a separate review pass, optional)
