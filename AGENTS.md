# Development rules / Entwicklungsregeln

Read SCOPE.md and docs/architecture.md before implementation. Clarify missing or
contradictory requirements; never infer product requirements from existing code.
Keep confirmed scope separate from implementation evidence. Preserve unrelated edits.

Implement plugin runtime under skills/<skill>/; shared runtime may live under
skills/_shared/ without a SKILL.md. Root scripts/ contains development tooling only.
Marketplace repositories own catalogs; plugin repositories never own catalogs.
Follow the layered tests described in tests/README.md. Add acceptance tests for
confirmed requirements. Generated structural tests do not establish product behavior.

Use verify for read-only checks and its explicit --review mode for scope/source
review. Do not execute target code as part of review. Run tests only as a separately
authorized development step and report actual results. Do not change scope to hide
implementation gaps. Never read private workspaces, credentials or ignored personal data.
Do not install tools, commit, push or publish without the corresponding authorization.

Vor Implementierung SCOPE.md und docs/architecture.md lesen. Fehlende Anforderungen
klären; fachliche Lücken nicht durch nachträgliche Soll-Änderungen verstecken.
Tests und Review getrennt behandeln. Bestehende Arbeit und private Daten erhalten.

## Current formats only / Nur aktuelle Formate

Only the current formats are supported: no legacy layouts, compatibility aliases, fallback discovery or automatic migrations.
Reject unsupported input explicitly before writes; preserve all existing user data.
Changes to rules may make an existing plugin fail verification. Update it only under
an explicit implementation request; never weaken scope to accept outdated content.
Nur aktuelle Formate: keine Altformat-Unterstützung, keine Aliase, keine stillen Migrationen.
Nicht unterstützte Eingaben mit konkretem Grund ablehnen, Nutzerdaten niemals löschen oder überschreiben.

## Website plugin additions / Website-Ergänzungen

- The plugin is `website-manager` (display name "Website Manager"). Website-project data formats (manifest `.project/specs/website.json`, schema copy `website.schema.json`, ownership record, optimize reports) are a separate interface and change only by an explicit requirement.
- `edit` stays limited to the start page and `publish` stays a placeholder until SCOPE.md says otherwise; planned functions are not implemented as a side effect of other work.
- Tests use no real website content and no private project data; tests use fictional fixtures.
- The shipped runtime has no built-in developer paths and no dependency on the source checkout (`www.draftmode`), `ai.plugins` or the Coach checkout.
- In authorized product use the runtime may read and edit the website project the user explicitly selected, within the contract of the respective skill. This is no general permission to read other private data.

Tests: keine echten Website-Inhalte oder privaten Projektdaten, nur fiktive Fixtures. Ausgelieferte Runtime: keine fest eingebauten Entwicklerpfade, keine Abhängigkeit zum Quellcheckout. Autorisierter Produktbetrieb: nur das ausdrücklich ausgewählte Websiteprojekt im Rahmen des Skill-Vertrags, keine pauschale Erlaubnis für andere private Daten.
