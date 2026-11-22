# Agent Plugins

The shared dev-team prompts are in `shared/dev-team/`. The host metadata is in `adapters/`.
The command `python3 scripts/build.py` generates `plugins/`, `.agents/plugins/marketplace.json`
and `.claude-plugin/marketplace.json`. Edit the sources of these files. Then generate them again.

Write all technical prose with the ASD-STE100 Simplified Technical English writing
rules. Technical prose includes README files, `AGENTS.md`, skills, role prompts,
references, code comments, docstrings, error messages, commit messages, PR
descriptions and issues. The ASD-STE100 controlled dictionary is optional. Use
short sentences, active voice and consistent terms. Preserve exact code, commands,
identifiers, quoted text and required technical terms. These are the only exceptions:

- Text that you quote or copy from a different source.
- Text that a tool generates, such as `CHANGELOG.md`.
- Legal text, such as a `LICENSE` file.

Use Python 3.11 or later and the standard library. To validate, run these commands:

```sh
python3 scripts/build.py --check
python3 scripts/check_skill_metadata.py
python3 -m unittest discover -s tests -v
```

Keep each plugin package self-contained. Do not create links that point outside a plugin root.
Make sure that plugin installation does not silently change permissions, authentication,
unrelated agent files or external services. Use temporary project directories to test
installers.

After the initial bootstrap, use this workflow for each change:

1. Create a branch.
2. Use signed Conventional Commits.
3. Use `gh` to open a GitHub PR.
4. Do not merge unless you get a request to merge.

Get an independent review of changes to scripts or agent behavior. Keep generated outputs
synchronized with their sources.
