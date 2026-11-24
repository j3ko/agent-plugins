# Agent Plugins

The shared dev-team prompts are in `shared/dev-team/`. The host metadata is in `adapters/`.
The command `python3 scripts/build.py` generates `plugins/`, `.agents/plugins/marketplace.json`
and `.claude-plugin/marketplace.json`. Edit the sources of these files. Then generate them again.

Load `/dev-team:orchestrate` (`$orchestrate` in Codex) before the first edit of each
task that ends in a PR.

Load `/dev-team:writing-for-agents` (`$writing-for-agents` in Codex) before you write
or edit technical prose: documentation, agent instructions, code comments, commit
messages, PR descriptions and issues. In this repository, technical prose also
includes docstrings and error messages.

The `writing-for-agents` and `retro` skills started as copies of upstream text. This
repository does not track that upstream. Thus, the copy exception does not apply to
these skills. When you edit one of these skills, rewrite each paragraph that you change
with the ASD-STE100 rules. Keep the `LICENSE` file of each skill.

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

Use signed Conventional Commits, and use `gh` to open each PR. Get an independent review
of each change to agent behavior. This includes a change to a skill, a role prompt, a
reference, the role metadata in `adapters/` or `shared/dev-team/plugin.toml`, or this
file.
