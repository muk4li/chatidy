# AUTH-006 – HTTP-Zugriffsgrenze (Entwurf, nicht erzwungen)

Stand: 2026-11-20. Quelle: Centrality ADR-007 und ADR-008.

## Zukünftiger Zugriff

Öffentlich: `/` (Landingpage), `/landing.css`, `/login` und
`/auth/callback`. Weitere öffentliche statische Assets müssen ausdrücklich
ergänzt werden, bevor Auth eingeschaltet wird.

Privat: `/app` und sämtliche Unterseiten; **jede** `/api/*`-Route,
unabhängig von HTTP-Methode oder Unterpfad, insbesondere:
- Chats, Nachrichten, Suche, Statistik und Export.
- Ordner, Regeln, intelligente Ordner, Tags, Vorschläge und Ollama.
- Upload, Vorschau, Bestätigung, Fortsetzung und Löschung von Importjobs.
- Neue zukünftige Daten-APIs sind standardmäßig privat.

`chatidy/access_policy.py` hält eine reine Klassifizierung und kann in
späteren Tests und im HTTP-Handler verwendet werden. **Sie ist derzeit nicht
in den Handler eingebunden.** Die APIs bleiben unauthentifiziert und dürfen
niemals über einen öffentlichen Reverse Proxy bereitgestellt werden.

## Sicherheitsanforderungen für den OIDC-PR

- Vor dem Lesen von Jobstatus, Aufruf der DB oder Start von Importarbeitern
  muss die serverseitig verifizierte Sitzung feststehen.
- Keine Benutzer-ID, Session oder Auth-Information aus unbeglaubigten
  HTTP-Headern oder Queryparametern übernehmen.
- Fehlende/falsche/gesperrte Identität: private GET/POST verweigern.
  Fremde Ressourcen auch bei gültiger Sitzung mit 404/keiner Auskunft behandeln.
- Aufrufvarianten und URL-Encoding gleich behandeln; sämtliche Methoden prüfen.
- Gleiche Chat-ID und Job-ID zweier Konten separat testen.
- Keine Behauptung über Login-Schutz, bevor der Handler tatsächlich ein Gate hat.
