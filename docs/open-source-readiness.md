# Open Source Readiness Checklist

Use this checklist before making this repository — or any repository derived from it —
publicly available. Each item must be confirmed as clear before publishing.

## Secrets and credentials

- [ ] No API keys, tokens, or passwords are committed anywhere in the repo.
- [ ] `.env` is listed in `.gitignore` and not tracked.
- [ ] `.env.example` contains only placeholder values (e.g., `sk-local-change-me`,
      `http://localhost:...`). Review it and confirm no real credentials are present.
- [ ] No secrets appear in git history. If any were committed in the past, rotate them
      and consider using `git filter-repo` to purge the history.

## Client and company information

- [ ] No client names, project names, or internal codenames appear in code, comments,
      docs, or commit messages.
- [ ] No internal URLs, IP addresses, or hostnames (beyond `localhost` examples) are
      present.
- [ ] No organization-specific infrastructure details (account IDs, bucket names,
      cluster names) are present.

## Sensitive rules and prompts

- [ ] `.github/skills/` contains only generic, reusable skills safe for public use.
- [ ] `.github/skills-external/` contains only vendored skills from public sources.
      Verify the license of each vendored skill allows redistribution.
- [ ] No commercially sensitive prompts, instructions, or business logic appear in
      governance files or adapter files.

## Workflows

- [ ] `.github/workflows/` contains no jobs that push to internal registries, deploy to
      private infrastructure, or use organization-specific secrets.
- [ ] No GitHub Pages or publication workflows are present (this template explicitly
      excludes them).
- [ ] CI workflows reference only public actions and public Docker images, or images
      that will remain accessible after the repo goes public.

## Generated and vendored content

- [ ] `skills-lock.json` contains only public skill references (no private registry
      URLs).
- [ ] `uv.lock` pins only packages from public indexes.
- [ ] No generated files contain embedded secrets or internal paths.

## Documentation

- [ ] `README.md` is accurate and self-contained for a public audience.
- [ ] `docs/` contains no internal design docs, meeting notes, or client-specific
      architecture diagrams.
- [ ] `memory/` files (`context.md`, `learnings.md`, `patterns.md`) have been reviewed
      and contain no sensitive project context. Consider clearing or sanitizing them
      before publishing.

## License

- [ ] A `LICENSE` file is present at the repo root.
- [ ] The chosen license is compatible with all vendored skills and dependencies.
- [ ] The license is confirmed with the team or legal counsel before publishing.

---

> **Note:** This checklist is a starting point, not a legal guarantee. Consult your
> organization's security and legal teams for a full review before publishing.
