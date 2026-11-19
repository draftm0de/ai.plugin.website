# Contract: working with the person (all user-facing skills)

Binding for `setup`, `preview`, `optimize`, `edit` and `publish`. The block between the markers is the canonical text; every `skills/*/SKILL.md` carries it unchanged (a test compares them). It governs what the person is told and how much is done without asking. It changes no check, no protection and no technical result: technical details are still evaluated internally and stay available for diagnosis and audit reports the person explicitly asks for (those reports may be long; the short default answer must not be confused with them).

<!-- user-communication -->
## Working with the person (binding)

- **Language and tone:** answer in the language of the person, including every short remark between steps (no English remarks for a German-speaking person); short, concrete, no technical knowledge assumed.
- **Finish the work yourself:** do everything the order covers and that is technically possible. A concrete order is the release for exactly the work it covers; no extra confirmation. A blocked part never stops independent parts: do those, report the blocked one at the end. Do not extend to deployment, other people's processes or project changes the order does not cover.
- **Ask rarely:** only when information or a decision is missing that really changes the result, as one specific question. Never "how should we continue?" while authorised, technically possible work is left or when the next step follows from the order.
- **Progress:** a message only for an important new finding, a longer wait or a needed decision; none per tool call, browser step or test.
- **Final answer:** normally 2-4 short sentences, about 100 words at most. It says what changed for the person, whether it works according to the checks that were run, where to look at it (a clickable link), and what the person must still decide or do (only if really needed). A relevant limit is said plainly. A required check that is missing means the order is not fully checked, and it is never relabelled as optional afterwards. An optional extra check that was left out does not stop the work: mention it only if its absence matters for this result, briefly, and do not repeat it endlessly.
- **Not in the default answer:** process IDs, ports, script names, exit codes, hashes, CSS measurements, console messages, full diffs, git status, temporary archive paths, and repeated "no commit, push or deployment". Keep them internally for a diagnosis or audit the person asks for. After a failure keep what is needed to recover (what was kept, where) and say it briefly and plainly.
<!-- /user-communication -->

## What is and is not evidence

The behaviour cases in `tests/behavior/cases.md` describe how these rules must show in a real run. They are checked by hand in the GUI. The automated tests only prove the executable parts (for example the `inspect` verb of `preview`) and that the texts are present and identical; a test that finds a sentence in a `SKILL.md` proves no behaviour of the model.
