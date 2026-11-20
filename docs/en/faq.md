# Frequently asked questions

[Deutsch](../de/faq.md) | **English**

[Home](../../README.en.md) · [Overview](README.md) · [Install](installation.md) · [Use](usage.md) · [Screens](screens.md) · [FAQ](faq.md)

## Product and access

**What is it?** The **Website Manager** plugin (`website-manager`) with five skills for static Astro websites: `setup`, `preview`, `optimize`, `edit`, `publish`. Claude and Codex are the target hosts; host acceptance is open (NOT RUN).

**Can I publish with it?** No. `publish` is a placeholder and says so explicitly. There is no publishing, no deployment and no forms.

**Can `edit` change my whole website project?** No, only the start page `src/pages/index.astro` of a site of type `astro-static`. Blog, further pages and new sites are not part of the skill.

**Is it installable?** The catalog entry `website` in the marketplace has been adjusted locally. Whether it is published and a host imports it is not evidenced ([Installation](installation.md)).

**Are there aliases such as `zyris-website` or `website-manager`?** No. Former plugin and skill names are not supported.

## Requirements

From the plugin's verified sources (details in the [prerequisites](../prerequisites.md)):

- **Python 3.10 or newer**, standard library only, no additional packages. Only Python 3.15 was run locally.
- **No Git required** for setup, preview, editing or optimization: no repository, commit or remote.
- **Node 22.23.4 or newer and npm** for the site's build and checks (`engines` of the generated `package.json`). You install the site's dependencies yourself (`npm install` or `npm ci` in the site folder) or through an explicit `setup verify`.
- **`ps` and `lsof`** for `preview`. If one is missing or cannot see its own process, `preview` reports `insufficient-evidence` and starts nothing.
- A **host browser tool** is useful for the visual check but not a prerequisite. Without an actual view the visual check stays open.

No skill installs tools (Node, npm, Git). `preview`, `optimize` and `edit` never install dependencies; only `setup verify` or `--build` runs the site's declared install, on explicit order.

## Privacy and persistence

**Where is my data?** Website data in your project; process state and backups in the temp area outside the repository; nothing in the installed plugin ([Storage](storage.md)).

**Are secrets shown in reports or in chat?** The skills put no secrets into files, command lines, reports or output. Known secret fields in tool output are redacted by pattern; this is not complete detection.

**Does the plugin read other private data?** Only the explicitly selected website project within the respective skill's contract. Tests use fictional fixtures only.

## Troubleshooting

- **`conflict` on `setup create`** for an existing site: either the inputs differ or a generated file was changed (for example by `edit`). That is the known limitation; nothing is overwritten. Use `setup verify`, which keeps the file (`modified (kept)`).
- **`needs-install`:** run `npm install` in the site folder yourself and start again.
- **`port-conflict`:** a process that does not belong to the plugin holds the port. `preview` neither ends nor adopts it; `inspect` checks the page served there.
- **`incomplete` in `optimize`:** a tool, a dependency, the lockfile, the build or readable output is missing. The assistant names the command (for example `npm ci`). `incomplete` is never reported as clean.
- **The work list stops the run:** it was edited by hand or damaged; restore it from your backup.
- **Project in the former format:** refused when the manifest references `zyris-website.schema.json` or only that schema file exists (without `website.schema.json`); convert the project yourself, there is no fallback. An unused old schema file next to a correctly used `website.schema.json` is not by itself a reason for refusal.
- **The assistant says “skill path not available” or “plugin path missing or outdated”:** update the plugin and open a new conversation. The assistant then does not search caches and does not copy scripts into your project.

## Validation limits

Structure and documentation checks evidence neither domain behaviour nor host acceptance. The following was **not** run (NOT RUN):

- real `npm`/Node runs on further Node versions (lower bound 22.23.4 and in-between versions) and platforms; only Node v26.12.1/npm 11.20.0 on Darwin arm64 was checked (see below);
- native Claude and Codex runs per skill, including skill loading, `${CLAUDE_SKILL_DIR}`, the effect of `allowed-tools` and reachability of `skills/_shared/`;
- model behaviour (fit of the order, missing facts, supplied instructions, routing);
- any actual visual check in a browser, including the effect of `"autoPort": false` in Claude Desktop.

What was run: deterministic tests with fictional fixtures, fake npm and local processes on `127.0.0.1` and, separately, real `npm`/Astro runs of `setup`, `optimize`, `edit` and `preview` on a fictional site (only the stated tool versions; [report](../migration/real-tools-acceptance.md)). They evidence the scripts' logic and the tool chain, not the behaviour of a host or model and no visual check. The full matrix per skill and host: [acceptance matrix](../migration/acceptance.md). Evidence for Claude never applies to Codex and vice versa.

---

Documentation prepared with Plugin Manager. Source-product ownership remains unchanged.
