# Installation and updates

[Deutsch](../de/installation.md) | **English**

[Home](../../README.en.md) · [Overview](README.md) · [Install](installation.md) · [Use](usage.md) · [Screens](screens.md) · [FAQ](faq.md)

## Choose your platform

Target hosts are **Claude** (Claude Desktop including the Code tab, Claude Code in a terminal) and **Codex** (desktop and terminal). The plugin is called `website` (display name “Website”). Like all plugins of this project it is installed through a **marketplace**: a catalog that points to the plugin repository. The catalog is **Draftmode AI Plugins** (`draftmode-ai-plugins`) at `https://github.com/draftm0de/ai.plugins`; the plugin repository is `https://github.com/draftm0de/ai.plugin.website`. There is no ZIP and no version or tag requirement. The marketplace itself is managed by the Plugin Manager (`/plugin-manager`); the Website plugin offers no function for it.

Important about the state:

- The catalog entry `website` has been adjusted locally. That it was pushed, that the plugin repository is reachable and that a host accepts the import is **not evidenced** (no network access, no host run).
- The steps below follow the installation contract of the Plugin Manager. The menu paths come from its documentation and user reports; they were **not** re-verified on a host for Website.
- Account, repository and organization policies still apply. Host evidence is **NOT RUN** ([acceptance matrix](../migration/acceptance.md)).

Prerequisites for use (Python, Git, Node/npm, `ps`/`lsof`) are in the [prerequisites](../prerequisites.md). No skill installs tools; `preview`, `optimize` and `edit` never install dependencies.

## Install

### Claude Desktop – including the Code tab

1. Open **Settings** (German interface: **Einstellungen**).
2. Select **Customize** and then **Plugins** (German: **Anpassungen**, **Plugins**).
3. Select **+ Add → Add marketplace** and **From a repository** (German: **+ Hinzufügen → Marketplace hinzufügen**, **Aus einem Repository hinzufügen**).
4. Enter `https://github.com/draftm0de/ai.plugins` as the **URL** and select **Sync**.
5. Select **Website** in the marketplace and install it.
6. Open a new conversation.

The labels follow the German interface as documented in the Manager contract; the English labels are translations and are not taken from a capture. In the Code tab, `/plugin …` commands only open the plugin settings according to the Manager documentation; use the settings path there.

### Claude Code in a terminal – alternative

The commands apply inside a session started with `claude`.

1. Add the marketplace:

   ```text
   /plugin marketplace add https://github.com/draftm0de/ai.plugins
   ```

2. Install the plugin and choose an installation scope:

   ```text
   /plugin install website@draftmode-ai-plugins
   ```

3. Open a new session. The skills are `setup`, `preview`, `optimize`, `edit` and `publish`; the exact invocation spelling depends on the host version and is not evidenced here by a host run.

### Codex Desktop

1. Open the **user icon** and select **Settings**.
2. Select **Integration → Plugins**.
3. Select **+ Add → A Marketplace**.
4. Enter `https://github.com/draftm0de/ai.plugins` and confirm.
5. Select **Website** and install it.

### Codex in a terminal – alternative

Run the commands directly in the shell.

1. Add the marketplace:

   ```sh
   codex plugin marketplace add https://github.com/draftm0de/ai.plugins
   ```

2. Install the plugin:

   ```sh
   codex plugin add website@draftmode-ai-plugins
   ```

3. Open a new Codex chat and check that the skills are available.

Whether both hosts install and reach the shared folder `skills/_shared/` and the sibling skill `skills/preview/` is **not evidenced** (NOT RUN). Without those files a skill stops with a message instead of guessing.

## Update

Sync the marketplace in your host's plugin settings and open a new conversation. In a terminal:

```text
/plugin marketplace update draftmode-ai-plugins
/plugin update website@draftmode-ai-plugins
```

```sh
codex plugin marketplace upgrade draftmode-ai-plugins
```

The manifests carry no version. A push alone does not prove that an installation has updated. A plugin update affects only the plugin's installation; it does not change your website projects. In authorized use, however, the skills do write data into the selected website project, each only within its contract ([Storage](storage.md)).

## Remove

Remove **Website** in the plugin settings, or in a terminal:

```text
/plugin uninstall website@draftmode-ai-plugins
```

```sh
codex plugin remove website@draftmode-ai-plugins
```

Removing the plugin deletes no website projects, reports or backups. Do not remove the whole marketplace if you use other plugins from it.

## Verify first use

In a Git project, open a new conversation and first ask for a preview of the changes: “Show me what creating the static website demo.example would change.” (`demo.example` is fictional; `plan` writes, installs and builds nothing.) Check that the assistant uses the `setup` skill and names the result. If the plugin is not offered, check repository access, marketplace sync and an app restart. A successful first use is an example, not host evidence of this repository.

---

Documentation prepared with Plugin Manager. Source-product ownership remains unchanged.
