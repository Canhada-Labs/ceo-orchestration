# {{PROJECT_NAME}} — Auto Memory

> **DEPRECATED AS A CONTENT FILE.** Auto memory lives in the Claude Code
> native location:
>
>     ~/.claude/projects/<project-slug>/memory/
>
> Claude Code loads `MEMORY.md` from that directory into every session
> automatically. This file stays in the repo only as a legacy pointer
> so existing installations that point at `./MEMORY.md` continue to find
> something; delete it from your repo once you've migrated.

## Where memory actually lives

For this project, the native memory location is:

    ~/.claude/projects/<slug>/memory/MEMORY.md

The CEO (Claude) writes entries to that location at session end. Each
topic memory is a separate file (`user_role.md`, `feedback_*.md`,
`project_*.md`, etc.) and `MEMORY.md` is an index that lists them with
one-line hooks.

See PROTOCOL.md §Handoff at end of session for the full write protocol,
and the ceo-orchestration skill §Memory Protocol for what to save vs.
what not to save.

## Migration from legacy MEMORY.md

If you have existing content in this file that predates Sprint 2:

1. Copy the content into `~/.claude/projects/<slug>/memory/legacy.md`
2. Update entries to one-file-per-topic under the same directory
3. Create a `MEMORY.md` index under that directory listing the topics
4. Delete this repo-root `MEMORY.md` from the commit (or leave it as
   a stub pointing at the native location — your choice)
