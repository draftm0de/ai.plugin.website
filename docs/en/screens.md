# Screens and examples

[Deutsch](../de/screens.md) | **English**

[Home](../../README.en.md) · [Overview](README.md) · [Install](installation.md) · [Use](usage.md) · [Screens](screens.md) · [FAQ](faq.md)

## Preview

There are **no** screenshots from Claude, Codex or a browser, and no interface has been accepted. The texts below are **fictional, illustrative examples** with fictional domains (`demo.example`); they are neither recorded host runs nor model output, and a real assistant's answers can differ.

```text
You:        Create a new static website for demo.example, title “Demo Workshop”.
Assistant:  The website demo.example is created and registered in the project. Install
            the dependencies with “npm install” in the folder sites/demo.example; then
            I can build and check. Nothing has been built or checked so far.
```

## Example walkthrough

Illustrative flow (fictional; the steps follow the skill contract, not a recorded run):

1. **Create** – `setup` reports `created`. Nothing was installed, built or committed.
2. **Check** – You install the dependencies; “Check demo.example.” runs `verify`. If npm reports exit 0 for install, build and check, the assistant may say “checked”; a step that did not run is called “not run”.
3. **Preview** – “Show me demo.example locally.” The assistant starts the dev server through the controller and names the address. If it did not open the page in a browser itself, it says: “The preview is running (not looked at yet).”
4. **Shape the start page** – “Shape the start page: name ‘Demo Workshop’, place ‘Sampletown’, offer bicycle repair.” After build and check, without its own visual check it reports: “The automatic checks passed, I could not look at the page myself.” Only with an actual look (including focus and keyboard operation of changed buttons and links) is the order “complete”.
5. **Audit** – “Check SEO and accessibility.” The assistant reports, for example, `clean-with-warnings`, names open findings with an ID (such as `SEO-001`) and asks whether you approve a proposal. The audit itself approves nothing.
6. **Approval and implementation** – “Approve SEO-001 and implement it.” The decision is stored, exactly the approved spot is changed and the full check runs again.
7. **Publish** – “Publish demo.example.” Answer: that is not available.

## Native screenshots

Real host screenshots are missing. They would be a host acceptance and are **NOT RUN**. The text examples above do not replace them and are not presented as such.

## Capture checklist

When real screenshots are made: record host and version, interface language, capture date and the input used; use fictional data only (no real website content, credentials or private paths); the caption names language, host and date; label real captures and fictional examples separately; the capture of an `edit` visual check shows the page that was actually changed, not a preview of the draft.

---

Documentation prepared with Plugin Manager. Source-product ownership remains unchanged.
