# Installation und Updates

**Deutsch** | [English](../en/installation.md)

[Start](../../README.md) · [Übersicht](README.md) · [Installation](installation.md) · [Nutzung](usage.md) · [Screens](screens.md) · [FAQ](faq.md)

## Plattform auswählen

Zielhosts sind **Claude** (Claude Desktop einschließlich Reiter Code, Claude Code im Terminal) und **Codex** (Desktop und Terminal). Das Plugin heißt `website` (Anzeigename „Website Manager“). Es wird wie alle Plugins dieses Projekts über einen **Marketplace** installiert: einen Katalog, der auf das Plugin-Repository verweist. Der Katalog ist **Draftmode AI Plugins** (`draftmode-ai-plugins`) unter `https://github.com/draftm0de/ai.plugins`; das Plugin-Repository ist `https://github.com/draftm0de/ai.plugin.website`. Es gibt kein ZIP und keine Versions- oder Tag-Pflicht. Den Marketplace selbst verwaltet der Plugin Manager (`/plugin-manager`); das Website-Plugin bietet dafür keine Funktion.

Wichtig zum Stand:

- Der Katalogeintrag `website` ist lokal angepasst. Dass er gepusht wurde, dass das Plugin-Repository erreichbar ist und dass ein Host den Import annimmt, ist **nicht belegt** (kein Netzwerkzugriff, kein Hostlauf).
- Die Schritte unten folgen dem Installationsvertrag des Plugin Managers. Die Menüpfade stammen aus dessen Dokumentation und Nutzerberichten; sie wurden für Website **nicht** erneut an einem Host geprüft.
- Konto-, Repository- und Organisationsrichtlinien gelten weiterhin. Die Hostnachweise sind **NOT RUN** ([Abnahmematrix](../migration/acceptance.md)).

Voraussetzungen für die Nutzung (Python, Git, Node/npm, `ps`/`lsof`) stehen in den [Voraussetzungen](../prerequisites.md). Kein Skill installiert Werkzeuge; `preview`, `optimize` und `edit` installieren nie Abhängigkeiten.

## Installieren

### Claude Desktop – einschließlich Reiter Code

1. Öffne **Einstellungen**.
2. Wähle **Anpassungen** und dort **Plugins**.
3. Wähle **+ Hinzufügen → Marketplace hinzufügen** und **Aus einem Repository hinzufügen**.
4. Trage `https://github.com/draftm0de/ai.plugins` als **URL** ein und wähle **Synchronisieren**.
5. Wähle im Marketplace **Website Manager** und installiere es.
6. Öffne eine neue Unterhaltung.

Die Bezeichnungen entsprechen der deutschen Oberfläche, wie sie im Manager-Vertrag dokumentiert sind. Im Reiter Code öffnen `/plugin …`-Befehle laut Manager-Dokumentation nur die Plugin-Einstellungen; nutze dort den Weg über die Einstellungen.

### Claude Code im Terminal – Alternative

Die Befehle gelten innerhalb einer mit `claude` gestarteten Sitzung.

1. Marketplace hinzufügen:

   ```text
   /plugin marketplace add https://github.com/draftm0de/ai.plugins
   ```

2. Plugin installieren und einen Installationsbereich wählen:

   ```text
   /plugin install website-manager@draftmode-ai-plugins
   ```

3. Öffne eine neue Sitzung. Die Skills heißen `setup`, `preview`, `optimize`, `edit` und `publish`; die genaue Aufrufschreibweise hängt von der Hostversion ab und ist hier nicht durch einen Hostlauf belegt.

### Codex Desktop

1. Öffne das **Benutzersymbol** und wähle **Settings**.
2. Wähle **Integration → Plugins**.
3. Wähle **+ Add → A Marketplace**.
4. Trage `https://github.com/draftm0de/ai.plugins` ein und bestätige.
5. Wähle **Website Manager** und installiere es.

### Codex im Terminal – Alternative

Führe die Befehle direkt in der Shell aus.

1. Marketplace hinzufügen:

   ```sh
   codex plugin marketplace add https://github.com/draftm0de/ai.plugins
   ```

2. Plugin installieren:

   ```sh
   codex plugin add website-manager@draftmode-ai-plugins
   ```

3. Öffne einen neuen Codex-Chat und prüfe, ob die Skills verfügbar sind.

Ob beide Hosts den gemeinsamen Ordner `skills/_shared/` und den Nachbarskill `skills/preview/` mitinstallieren und erreichen, ist **nicht belegt** (NOT RUN). Ohne diese Dateien bricht ein Skill mit einer Meldung ab, statt zu raten.

## Aktualisieren

Synchronisiere den Marketplace in den Plugin-Einstellungen deines Hosts und öffne eine neue Unterhaltung. Im Terminal:

```text
/plugin marketplace update draftmode-ai-plugins
/plugin update website-manager@draftmode-ai-plugins
```

```sh
codex plugin marketplace upgrade draftmode-ai-plugins
```

Die Manifeste tragen keine Version. Ein Push allein beweist nicht, dass eine Installation aktualisiert wurde. Ein Plugin-Update betrifft nur die Installation des Plugins; es ändert deine Websiteprojekte nicht. Im autorisierten Betrieb schreiben die Skills dagegen sehr wohl Daten in das ausgewählte Websiteprojekt, jeweils nur im Rahmen ihres Vertrags ([Speicherung](storage.md)).

## Entfernen

Entferne **Website Manager** in den Plugin-Einstellungen, oder im Terminal:

```text
/plugin uninstall website-manager@draftmode-ai-plugins
```

```sh
codex plugin remove website-manager@draftmode-ai-plugins
```

Das Entfernen des Plugins löscht keine Websiteprojekte, Berichte oder Sicherungen. Entferne nicht den ganzen Marketplace, wenn du weitere Plugins daraus nutzt.

## Erste Nutzung prüfen

Öffne in einem Git-Projekt eine neue Unterhaltung und bitte zunächst um eine Vorschau der Änderungen: „Zeig mir, was ein Anlegen der statischen Website demo.example ändern würde.“ (`demo.example` ist erfunden; `plan` schreibt, installiert und baut nichts.) Prüfe, dass der Assistent den Skill `setup` verwendet und das Ergebnis nennt. Wird das Plugin nicht angeboten, prüfe Repositoryzugriff, Marketplace-Synchronisierung und einen Neustart der App. Eine gelungene erste Nutzung ist ein Beispiel, kein Hostnachweis dieses Repositories.

---

Dokumentation erstellt mit Plugin Manager. Die Urheberschaft des beschriebenen Produkts bleibt unverändert.
