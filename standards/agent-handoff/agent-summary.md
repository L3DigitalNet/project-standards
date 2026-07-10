# Agent Handoff Summary

Use `.agents/skills/agent-handoff/SKILL.md` for operating procedure. Keep current status and tasks in `docs/STATUS.md` and `docs/TODO.md`; keep only in-flight work and active incidents in `docs/handoff/state.md`; route durable facts to the matching lazy document.

Do not reread state already injected by a SessionStart hook. Never read home-directory globals or sibling repositories for project handoff. Store credential references only, never values.

At closeout, update only changed facts, append a compact session record when useful, maintain stable numeric bug records and their index, and run relevant validation.
