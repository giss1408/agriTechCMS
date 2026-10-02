import 'dart:async';

import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:uuid/uuid.dart';

import 'api_client.dart';
import 'local_db.dart';
import 'models.dart';

const appVersion = '0.1.0';

/// App-wide state: session, connectivity and the sync loop. Screens listen to it.
class AppState extends ChangeNotifier {
  AppState._(this.db, this.api, this._prefs, this.deviceId);

  static Future<AppState> create() async {
    final prefs = await SharedPreferences.getInstance();
    var deviceId = prefs.getString('device_id');
    if (deviceId == null) {
      deviceId = const Uuid().v4();
      await prefs.setString('device_id', deviceId);
    }
    final state = AppState._(await LocalDb.open(), ApiClient(prefs), prefs, deviceId);
    await state._loadCounters();
    state._watchConnectivity();
    return state;
  }

  final LocalDb db;
  final ApiClient api;
  final SharedPreferences _prefs;
  final String deviceId;

  bool online = false;
  bool syncing = false;
  int pendingCount = 0;
  int producerCount = 0;
  String? lastSyncError;
  DateTime? lastSyncAt;
  double maxMoisture = 8.0;
  double maxWeight = 1000;

  StreamSubscription<List<ConnectivityResult>>? _connSub;
  Timer? _timer;

  bool get loggedIn => api.isLoggedIn;

  Future<void> _loadCounters() async {
    pendingCount = await db.pendingCount();
    producerCount = await db.producerCount();
    final last = await db.get('last_sync_at');
    lastSyncAt = last == null ? null : DateTime.parse(last);
    maxMoisture = double.tryParse(await db.get('max_moisture') ?? '') ?? maxMoisture;
    maxWeight = double.tryParse(await db.get('max_weight') ?? '') ?? maxWeight;
    notifyListeners();
  }

  void _watchConnectivity() {
    _connSub = Connectivity().onConnectivityChanged.listen((results) {
      final wasOnline = online;
      online = results.any((r) => r != ConnectivityResult.none);
      notifyListeners();
      if (online && !wasOnline) unawaited(sync()); // back in coverage: send what was recorded offline
    });
    Connectivity().checkConnectivity().then((results) {
      online = results.any((r) => r != ConnectivityResult.none);
      notifyListeners();
    });
    // Safety net: some phones report connectivity changes late or never.
    _timer = Timer.periodic(const Duration(minutes: 3), (_) {
      if (pendingCount > 0) unawaited(sync());
    });
  }

  // ---------------------------------------------------------------- session

  Future<String?> requestCode(String phone) => api.requestOtp(phone);

  Future<void> login(String phone, String code) async {
    await api.verifyOtp(phone, code, deviceId);
    notifyListeners();
    await sync(full: producerCount == 0);
  }

  /// Logging out never deletes the outbox: unsent collections are sent after the next login.
  Future<void> logout() async {
    await api.clearSession();
    notifyListeners();
  }

  // ---------------------------------------------------------------- collections

  Future<void> record(LocalCollection c) async {
    await db.saveCollection(c);
    pendingCount = await db.pendingCount();
    notifyListeners();
    if (online) unawaited(sync());
  }

  Future<void> discard(String clientUuid) async {
    await db.deleteCollection(clientUuid);
    pendingCount = await db.pendingCount();
    notifyListeners();
  }

  // ---------------------------------------------------------------- sync

  /// Push first (the collector's work is what matters), then pull reference data and statuses.
  /// Returns a short French summary for a snackbar.
  Future<String> sync({bool full = false}) async {
    if (syncing || !loggedIn) return '';
    syncing = true;
    lastSyncError = null;
    notifyListeners();
    var sent = 0, rejected = 0;
    try {
      final pending = await db.pending();
      for (var i = 0; i < pending.length; i += 100) {
        final chunk = pending.sublist(i, i + 100 > pending.length ? pending.length : i + 100);
        final result = await api.push({
          'device_id': deviceId,
          'device_time': DateTime.now().toUtc().toIso8601String(),
          'app_version': appVersion,
          'pending_on_device': pending.length - i,
          'collections': chunk.map((c) => c.toApi()).toList(),
        });
        for (final a in (result['accepted'] as List).cast<Map<String, dynamic>>()) {
          await db.markSynced(a['client_uuid'] as String, a);
          sent++;
        }
        for (final r in (result['rejected'] as List).cast<Map<String, dynamic>>()) {
          await db.markRejected(r['client_uuid'] as String, r['code'] as String, r['message'] as String);
          rejected++;
        }
      }

      final cursor = full ? null : await db.get('cursor');
      final data = await api.pull(cursor, deviceId);
      await db.upsertProducers((data['producers'] as List).cast<Map<String, dynamic>>());
      await db.replacePrices((data['prices'] as List).cast<Map<String, dynamic>>());
      await db.applyServerStatuses((data['collections'] as List).cast<Map<String, dynamic>>());
      final settings = data['settings'] as Map<String, dynamic>;
      await db.set('max_moisture', settings['max_moisture_percent'].toString());
      await db.set('max_weight', settings['max_weight_kg'].toString());
      await db.set('cursor', data['cursor'] as String);
      await db.set('last_sync_at', DateTime.now().toUtc().toIso8601String());
    } on ApiException catch (e) {
      lastSyncError = e.message;
    } finally {
      syncing = false;
      await _loadCounters();
    }
    if (lastSyncError != null) return lastSyncError!;
    final parts = <String>[
      if (sent > 0) '$sent collecte(s) envoyée(s)',
      if (rejected > 0) '$rejected refusée(s) — à corriger',
    ];
    return parts.isEmpty ? 'Données à jour' : parts.join(', ');
  }

  @override
  void dispose() {
    _connSub?.cancel();
    _timer?.cancel();
    super.dispose();
  }

  String get greetingName => api.userName ?? '';
  String get cooperativeName => api.cooperativeName ?? '';
  SharedPreferences get prefs => _prefs;
}
