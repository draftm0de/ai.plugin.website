# Screens und Beispiele

**Deutsch** | [English](../en/screens.md)

[Start](../../README.md) · [Übersicht](README.md) · [Installation](installation.md) · [Nutzung](usage.md) · [Screens](screens.md) · [FAQ](faq.md)

## Vorschau

Es liegen **keine** Screenshots aus Claude, Codex oder einem Browser vor, und es wurde keine Oberfläche abgenommen. Die Texte unten sind **erfundene, illustrative Beispiele** mit fiktiven Domains (`demo.example`); sie sind weder aufgezeichnete Hostläufe noch Modellausgaben, und die Antworten eines echten Assistenten können abweichen.

```text
Du:         Lege eine neue statische Website für demo.example an, Titel „Demo Werkstatt“.
Assistent:  Die Website demo.example ist angelegt und im Projekt eingetragen. Installiere
            die Abhängigkeiten mit „npm install“ im Ordner sites/demo.example; danach
            kann ich bauen und prüfen. Bisher wurde nichts gebaut oder geprüft.
```

## Beispielablauf

Illustrativer Ablauf (erfunden; die Schritte entsprechen dem Skillvertrag, nicht einem aufgezeichneten Lauf):

1. **Anlegen** – `setup` meldet `created`. Es wurde nichts installiert, gebaut oder committet.
2. **Prüfen** – Du installierst die Abhängigkeiten; „Prüfe demo.example.“ führt `verify` aus. Meldet npm bei der Prüfung Exit 0 für Installation, Build und Check, darf der Assistent „geprüft“ sagen; ein Schritt, der nicht lief, heißt „nicht gelaufen“.
3. **Vorschau** – „Zeig mir demo.example lokal.“ Der Assistent startet den Dev-Server über den Controller und nennt die Adresse. Hat er die Seite nicht selbst im Browser geöffnet, sagt er: „Die Vorschau läuft (noch nicht angesehen).“
4. **Startseite gestalten** – „Gestalte die Startseite: Name ‚Demo Werkstatt‘, Ort ‚Musterstadt‘, Angebot Fahrradreparatur.“ Nach Build und Check meldet er ohne eigene Sichtprüfung: „Die automatischen Prüfungen sind bestanden, ich konnte die Seite nicht selbst ansehen.“ Erst mit tatsächlicher Ansicht (Fokus und Tastaturbedienung geänderter Schaltflächen und Links inklusive) ist der Auftrag „vollständig“.
5. **Audit** – „Prüfe SEO und Barrierefreiheit.“ Der Assistent meldet z. B. `clean-with-warnings`, nennt offene Befunde mit ID (etwa `SEO-001`) und fragt, ob du einen Vorschlag freigibst. Der Audit selbst gibt nichts frei.
6. **Freigabe und Umsetzung** – „Gib SEO-001 frei und setze es um.“ Die Entscheidung wird gespeichert, genau die freigegebene Stelle geändert und die Prüfung erneut vollständig ausgeführt.
7. **Veröffentlichen** – „Veröffentliche demo.example.“ Antwort: Das ist nicht verfügbar.

## Echte Screenshots

Echte Host-Screenshots fehlen. Sie wären eine Hostabnahme und sind **NOT RUN**. Die Textbeispiele oben ersetzen sie nicht und werden nicht als solche ausgegeben.

## Aufnahmecheckliste

Wenn echte Screenshots entstehen: Host und Version, Oberflächensprache, Aufnahmedatum und die verwendete Eingabe festhalten; nur fiktive Daten verwenden (keine echten Websiteinhalte, Zugangsdaten oder privaten Pfade); die Beschriftung nennt Sprache, Host und Datum; echte Aufnahmen und erfundene Beispiele getrennt kennzeichnen; die Aufnahme einer Sichtprüfung von `edit` zeigt die tatsächlich geänderte Seite, nicht eine Vorschau des Entwurfs.

---

Dokumentation erstellt mit Plugin Manager. Die Urheberschaft des beschriebenen Produkts bleibt unverändert.
