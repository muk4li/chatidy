# AUTH-006 – HTTP-Zugriffsgrenze (in L2 integriert, noch nicht produktiv freigegeben)

Stand: 2026-11-20. Quelle: Centrality ADR-007 und ADR-008.

## Zugriff im optionalen Authentik-Modus

Öffentlich: `/` (Landingpage), `/landing.css`, `/login` und
`/auth/callback`. Weitere öffentliche statische Assets müssen ausdrücklich
ergänzt werden, bevor Auth eingeschaltet wird.

Privat: `/app` und sämtliche Unterseiten; **jede** `/api/*`-Route,
unabhängig von HTTP-Methode oder Unterpfad, insbesondere:
- Chats, Nachrichten, Suche, Statistik und Export.
- Ordner, Regeln, intelligente Ordner, Tags, Vorschläge und Ollama.
- Upload, Vorschau, Bestätigung, Fortsetzung und Löschung von Importjobs.
- Neue zukünftige Daten-APIs sind standardmäßig privat.

`chatidy/access_policy.py` klassifiziert die Routen; seit Integration
#52 ist die Policy bei aktiviertem `CHATIDY_AUTH_REQUIRED=1` in den
HTTP-Handler eingebunden und prüft Sessions bevor die Kontobibliothek
geöffnet wird. **Ohne Authentik-Modus** bleibt nur der lokale
Einzelnutzerbetrieb über `127.0.0.1` erlaubt. Ein öffentlicher
Reverse-Proxy-Betrieb ist trotz integriertem Code noch nicht freigegeben.

## Sicherheitsanforderungen vor öffentlicher Freigabe

- Vor dem Lesen von Jobstatus, Aufruf der DB oder Start von Importarbeitern
  muss die serverseitig verifizierte Sitzung feststehen.
- Keine Benutzer-ID, Session oder Auth-Information aus unbeglaubigten
  HTTP-Headern oder Queryparametern übernehmen.
- Fehlende/falsche/gesperrte Identität: private GET/POST verweigern.
  Fremde Ressourcen auch bei gültiger Sitzung mit 404/keiner Auskunft behandeln.
- Aufrufvarianten und URL-Encoding gleich behandeln; sämtliche Methoden prüfen.
- Gleiche Chat-ID und Job-ID zweier Konten separat testen.
- Keine Behauptung über Login-Schutz, bevor der Handler tatsächlich ein Gate hat.

## Deep-Link-Grenzen aus F-009

Alle Bibliotheksunterpfade `/app/import`, `/app/inbox`, `/app/archive`,
`/app/unfiled`, `/app/topics`, `/app/folders/<id>`, `/app/smart/<id>`
und `/app/chats/<id>` liefern dieselbe SPA. Der Server schützt sie im
Authentik-Modus mit derselben verifizierten Sitzung wie `/app`.
Die IDs beziehen sich ausschließlich auf die getrennte Bibliothek dieses
Kontos und sind keine Berechtigung oder Benutzerkennung.
