# Summary and Receipt Formats

Two fixed layouts, so reports are comparable across sessions, agents, and repositories: the **operator summary** for a requested view of open work, and the **creation receipt** for a single issue or PR that was just created. `gh-workflow summary` and `gh-workflow receipt` render these layouts from live state; relay that output verbatim rather than reformatting it. When rendering by hand, follow the layouts exactly.

Braced tokens such as `{number}` are substitution points, not literal text. Show an empty optional cell as `—`; never invent a value to fill one.

## Operator summary

Attention first. The summary exists to drive operator decisions, so what needs a human comes before the inventory of everything else.

Order of sections is fixed:

1. **Scope header** — the target, the timestamp of the read, and the counts it covers.
2. **Needs attention** — work that is stuck, underspecified, inconsistent, or late.
3. **Issues** — the open issue inventory.
4. **Pull requests** — the open PR inventory.
5. **Discovered follow-ups** — durable work found while assembling the summary.

```markdown
# {target} — work state

Read {timestamp} · {open_issue_count} open issues · {open_pr_count} open PRs

## Needs attention

- **Blocked** — {number} {title}: {blocker}
- **Needs definition** — {number} {title}: {what is missing}
- **Terminal-sync mismatch** — {number} {title}: Workflow {value} vs GitHub {state}/{reason}
- **Target date passed** — {number} {title}: {target_date}

## Issues

| Issue | Type | Title | Workflow | Priority | Size / Severity | Execution mode |
| --- | --- | --- | --- | --- | --- | --- |
| {number} | {type} | {title} | {workflow} | {priority} | {size_or_severity} | {execution_mode} |

## Pull requests

| PR       | Title   | Governing issue   | State   | CI   | Risk notes   |
| -------- | ------- | ----------------- | ------- | ---- | ------------ |
| {number} | {title} | {governing_issue} | {state} | {ci} | {risk_notes} |

## Discovered follow-ups

- {description} — {disposition}
```

Section rules:

- **Scope header.** `{target}` is the repository or the scope actually queried; `{timestamp}` is when live state was read, not when the summary was written. Counts describe what the tables below contain.
- **Needs attention.** Exactly four categories, in the order shown: Blocked, Needs definition, terminal-sync mismatches (a `Workflow` value that disagrees with the GitHub open/closed state and close reason), and passed target dates. Categories with no members are omitted; when all four are empty, keep the section and say so in one line rather than dropping it.
- **Issues.** `Size / Severity` carries `Severity` for Bugs and `Size` for every other Type — one column, because Severity is the value that column asks for on a Bug. A Bug pins both fields (see the pinning matrix in [field-vocabulary.md](field-vocabulary.md)); the column reports `Severity` and its `Size` simply is not surfaced here.
- **Pull requests.** `Governing issue` is the linked Issue or `—` when the PR has none; a missing link on a nontrivial PR belongs in Needs attention as well.
- **Discovered follow-ups.** Work noticed while summarizing. Each entry states its disposition: filed as an Issue with its number, or proposed and awaiting the operator's decision. This tail is a handoff, not a list to act on unilaterally.

A summary is a read. It never mutates anything, and the read-only exemption does not extend to presenting one: the layout is what makes summaries comparable, so the skill loads before rendering.

## Creation receipt

Present the receipt immediately after creating an issue or PR — creation is when metadata gaps are cheapest to fix, and the receipt lets the operator verify the work contract without opening GitHub.

```text
Created {kind} #{number} — {title}
{link}

Type: {type} | Workflow: {workflow} | Priority: {priority}
Size / Severity: {size_or_severity} | Change risk: {change_risk}
Execution mode: {execution_mode} | Target date: {target_date}

Gaps: {gaps}
```

For a PR the field block instead carries what a PR actually has:

```text
Created PR #{number} — {title}
{link}

Governing issue: {governing_issue} | Draft: {yes_or_no} | CI: {ci_status}

Gaps: {gaps}
```

Receipt rules:

- **Header.** Kind (`issue` or `PR`), number, title, and the link on its own line.
- **Fields.** Report the values actually set, not the values intended. An unset field appears as `—` rather than being dropped, so the operator sees the hole.
- **Gaps.** One line naming what is still missing: pinned fields without values for this Type per the pinning matrix, absent acceptance criteria, or a missing governing-Issue link on a nontrivial PR. When nothing is missing, the line reads `Gaps: none`. Never omit the line — a silent receipt is indistinguishable from an unchecked one.

Receipts are bound to creation. Ordinary edits do not get one; use a summary when a broader view is wanted.
