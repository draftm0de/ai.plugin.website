# Initialisierung durch `setup create` (Vorbereitung Etappe 2, entschieden durch D-16 bis D-18)

Migrationsnachweis zur bestätigten Initialisierungsregel (decisions.md D-13, SCOPE R5); in Etappe 2 umgesetzt. Keine zweite Produktdefinition.

**Entscheidungsstand (Etappe 2, 2026-11-19):** Die offenen Felder O1–O3 sind entschieden: `$schema` wird geschrieben (`./website.schema.json`, D-16/D-17), `title` und `aliases` werden wie im Bestand geschrieben (Titel = Domain, wenn nicht angegeben; `[]`, wenn kein Alias; die Empfehlung, sie wegzulassen, ist **nicht beauftragt**), `port` wird immer geschrieben (ausdrücklich, sonst automatisch; Regel unten). Die Tabelle und die Empfehlung weiter unten sind der historische Stand vor der Entscheidung; maßgeblich sind D-16 bis D-18 in `decisions.md` und `SCOPE.md` R5.

**Portregel (D-16):** leeres Projekt 4321; sonst der höchste *effektive* Port + 1 (effektiv = expliziter Port oder 4321 + Position, wie im Resolver); Kollisionen mit effektiven Ports werden abgelehnt; ein Ergebnis über 65535 stoppt konkret (`--port` wählen).

**Altformat (D-18):** Verweis auf `./zyris-website.schema.json` oder nur eine alte Schemadatei → `invalid` ohne Schreiben, keine Migration, kein Fallback.

**Bestätigt (D-13) ist nur die Regel:** Bei einem neuen Websiteprojekt legt `setup create` ein fehlendes Manifest selbst an – nach dem aktuellen Schema, mit den bestätigten Angaben der neuen Site, ohne bestehende Dateien zu überschreiben, ohne unbekannte fachliche Angaben zu erfinden. Alles Weitere unten ist Herkunftsanalyse oder Empfehlung.

## Herkunftsklassen

- **S** = vom Plugin-Schema erforderlich (`skills/_shared/resources/website.schema.json` (bis Etappe 1: `zyris-website.schema.json`, D-17)).
- **B** = aus bestehender Vorlage/Implementierung der Quelle beobachtet (Belegstellen in `www.draftmode`: `templates/setup/_manifest/…`, `types.json`, `static_setup.py`), **nicht** fachlich bestätigt.
- **N** = Nutzerangabe im Aufruf (bestätigte Angabe der neuen Site).
- **O** = offen, Empfehlung unten.

## Feldbelegung

| Feld | Wert | S | B | N | Status |
|---|---|---|---|---|---|
| `version` | `1` | erforderlich (`const: 1`) | ja | – | festgelegt durch Schema |
| `components` | Liste mit genau dem neuen Eintrag | erforderlich | ja (Vorlage startet mit `[]`) | – | festgelegt durch Schema |
| `$schema` | ~~`./zyris-website.schema.json`~~ → `./website.schema.json` (D-17) | **nicht erforderlich** (optional, Typ string) | ja (Vorlage setzt es) | – | **offen (O1)** |
| `name` | angegebene Domain | erforderlich, Muster | ja | `setup create <domain>` | bestätigt als Nutzerangabe |
| `path` | `<sites-Ordner>/<domain>` | erforderlich, Muster | ja | `--path`, sonst Default `sites` (B: `types.json`) | Wert aus Nutzerangabe; der Default `sites` ist beobachtet, nicht bestätigt |
| `type` | `astro-static` | erforderlich, einziger Wert | ja | `--type` | bestätigt (D-01/D-06, R21) |
| `title` | – | optional | ja (schreibt Domain, wenn `--title` fehlt) | `--title` | **offen (O2)** |
| `aliases` | `--alias`-Werte | optional | ja (schreibt `[]`) | `--alias` | nur bei Angabe; leer ist kein erfundener Wert, ob `[]` geschrieben wird, folgt aus O2-Logik: weglassen empfohlen |
| `port` | – | optional (1024–65535) | ja (höchster Port+1, sonst 4321) | `--port` | **offen (O3)** |
| `environment` | – | optional | nur bei Angabe | `--environment` | nur bei Angabe, sonst weggelassen |
| Schema-Kopie `.project/specs/website.schema.json` (vor D-17: `zyris-website.schema.json`) | Kopie des Plugin-Schemas | – | ja (nur bei Fehlen; fremde Kopie → `conflict`) | – | durch SCOPE R5/R8 festgelegt |

Nicht zu erfinden: Titel jenseits der Nutzerangabe, Aliase, Umgebung, Kontaktdaten, Inhalte.

## Verhalten (aus setup-Vertrag §3/§6 und R5/R8)

- Vorhandenes Manifest bleibt unverändert, außer dem Anhängen der neuen Komponente; ungültig → STOP vor jedem Schreiben; vorhandene Einträge werden nie geändert.
- Schreibreihenfolge: Site-Dateien, Scratch, Schema-Kopie, Besitzprotokoll, **Manifest zuletzt**; das entstehende Manifest wird vor dem Schreiben gegen das Plugin-Schema validiert.
- Zu testen in Etappe 2: Manifest fehlt/vorhanden; Schema-Kopie fehlt/gleich/fremd; Port- und Alias-Kollision; ungültiger Name.

## Empfehlung zu den drei offenen Feldern (nicht entschieden)

Ergebnis bei `setup create alpha.example --type astro-static` ohne weitere Optionen in einem neuen Projekt:

```json
{
  "$schema": "./website.schema.json",
  "version": 1,
  "components": [
    { "name": "alpha.example", "path": "sites/alpha.example", "type": "astro-static", "port": 4321 }
  ]
}
```

| Feld | Empfehlung | Auswirkung bei Zustimmung | Auswirkung der Alternative |
|---|---|---|---|
| **O1 `$schema`** | **Schreiben:** `"./zyris-website.schema.json"` | Editoren validieren gegen die daneben angelegte Schema-Kopie; kein Einfluss auf die verbindliche Prüfung (Plugin-Schema); entspricht dem bisherigen Format, es bleibt R4/R21-konform. Kein erfundener Inhalt: es verweist nur auf die Datei, die `setup` selbst anlegt | Weglassen: gültig (optional), aber Editor-Validierung entfällt und neue Manifeste unterscheiden sich im Aufbau von bestehenden |
| **O2 `title`** | **Nur bei `--title` schreiben**, sonst weglassen (der Resolver verwendet dann `name`) | Kein stellvertretender Titel; Auswahl per Titel/Domain unverändert; Template-Rendering nutzt weiter `--title` oder die Domain | Immer die Domain als Titel schreiben (wie die Quelle): Duplikat von `name`, später nicht von einer echten Titelwahl unterscheidbar |
| **O3 `port`** | **Immer schreiben:** `--port`, sonst höchster vorhandener Port + 1, sonst 4321 | Stabiler, kollisionsgeprüfter Port; ohne ihn leitet der Resolver `4321 + Index` ab, was sich bei Umsortieren/Entfernen von Sites ändert und `preview` die Zuordnung verschieben kann. Der Wert ist ein abgeleiteter Default, keine Fachangabe | Weglassen: minimales Manifest, aber Port hängt von der Reihenfolge ab |

Folge für `aliases`: nur schreiben, wenn `--alias` angegeben ist (konsistent mit O2). Bis zur Entscheidung gilt: keine der drei Empfehlungen ist bestätigt.
