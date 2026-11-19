# Tests / Tests

Use `make test` for deterministic unit, integration and contract checks. `make test-unit`, `make test-integration` and `make test-contracts` select a layer. `make test-native` is separate and requires isolated host profiles; `make test-behavior` is only for explicitly authorized model tests. Missing suites report `NOT RUN`, not acceptance. No model or host test is included by default.

`make test` prüft deterministische Unit-, Integrations- und Vertragstests. Einzelbereiche: `make test-unit`, `make test-integration`, `make test-contracts`. Native Host- und Modelltests sind ausdrücklich getrennt. Fehlende Suiten melden `NOT RUN`, keine erfolgreiche Abnahme.

Place tests under `tests/unit/`, `tests/integration/`, `tests/contracts/`, `tests/native/` or `tests/behavior/`, with optional skill/component subdirectories. Add `__init__.py` to discovered unittest directories. Fictional data belongs under `tests/fixtures/`, helpers under `tests/support/`. Create only needed directories. The scaffold provides structural contract checks only; add actual product tests before claiming behavior acceptance.

Tests nach Testart und bei Bedarf nach Skill/Komponente ablegen. In unittest-Verzeichnissen `__init__.py` ergänzen. Fiktive Daten: `tests/fixtures/`; Helfer: `tests/support/`. Nur benötigte Ordner anlegen. Das Gerüst enthält ausschließlich Strukturverträge; Produktverhalten benötigt eigene Tests.

## Normal run vs. separately released real-npm tests / Normaler Lauf und getrennt freizugebende echte npm-Tests

- **Normal (deterministic):** `make test`, `python3 -B scripts/run_tests.py [--kind deterministic|unit|integration|contracts]`. Only `tests/unit`, `tests/integration`, `tests/contracts`. All `npm` calls are fakes; no network. An inherited variable such as `ZW_REAL_NPM=1` has no effect (regression test `tests/contracts/test_external_separation.py`).
- **Separate (real npm, network, downloads):** `tests/external/` is not a layer of any default run and not a native host test. It runs only through `python3 -B scripts/run_external_tests.py --approved` after the owner released it separately; the runner enables the tests by a module flag, not by an environment variable. Without `--approved` it prints `NOT RUN` and exits 2.
- Skipped tests are never counted as passed; the external suite reports `NOT RUN` unless it was run through its runner.

Normal: `make test` bzw. `scripts/run_tests.py` (nur `unit`, `integration`, `contracts`, alle `npm`-Aufrufe sind Attrappen, kein Netzwerk; geerbte Variablen ändern nichts). Getrennt: `tests/external/` nur über `scripts/run_external_tests.py --approved` nach gesonderter Freigabe. Übersprungene Tests gelten nie als bestanden.

