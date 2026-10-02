# Cabosse Collecte — collector app

Flutter app for field collectors: offline-first weighing entry, QR scan of producer cards, GPS, sync.
UI in French, large touch targets for field use.

```bash
flutter pub get
flutter run                                              # emulator: API at http://10.0.2.2:8000/v1
flutter run --dart-define=API_URL=http://<lan-ip>:8000/v1  # real phone on the same Wi-Fi
flutter analyze && flutter test
```

Code map: `lib/logic.dart` (pure rules, unit-tested), `lib/data/` (SQLite outbox, API client, sync loop in
`app_state.dart`), `lib/screens/`. Protocol: [docs/technical/05-offline-sync.md](../../docs/technical/05-offline-sync.md).
