import 'dart:async';
import 'dart:convert';

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
  int pendingIssues = 0;
  int producerCount = 0;
  String? lastSyncError;
  DateTime? lastSyncAt;
  double maxMoisture = 8.0;
  double maxWeight = 1000;

  StreamSubscription<List<ConnectivityResult>>? _connSub;
  Timer? _timer;
  DateTime? _lastPullAt;
  // After a failed automatic attempt, wait 1, 2, 4… up to 30 minutes: no data burnt retrying on a dead link.
  int _failures = 0;
  DateTime? _nextAutoAttempt;

  // Small batches: on a flaky link each batch that gets through is saved, instead of losing one big upload.
  static const _pushBatch = 25;
  // Reference data changes rarely; automatic syncs refresh it at most this often.
  static const _autoPullEvery = Duration(minutes: 15);

  bool get loggedIn => api.isLoggedIn;

  Future<void> _loadCounters() async {
    pendingCount = await db.pendingCount();
    pendingIssues = (await _issueQueue()).length;
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
      if (online && !wasOnline) {
        _failures = 0; // a new network: try right away
        unawaited(sync(auto: true)); // back in coverage: send what was recorded offline
      }
    });
    Connectivity().checkConnectivity().then((results) {
      online = results.any((r) => r != ConnectivityResult.none);
      notifyListeners();
    });
    // Safety net: some phones report connectivity changes late or never.
    _timer = Timer.periodic(const Duration(minutes: 3), (_) {
      if (pendingCount > 0 || pendingIssues > 0) unawaited(sync(auto: true));
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
    if (online) unawaited(sync(auto: true));
  }

  Future<void> discard(String clientUuid) async {
    await db.deleteCollection(clientUuid);
    pendingCount = await db.pendingCount();
    notifyListeners();
  }

  // ---------------------------------------------------------------- problem reports

  Future<List<Map<String, dynamic>>> _issueQueue() async =>
      (jsonDecode(await db.get('issue_queue') ?? '[]') as List).cast<Map<String, dynamic>>();

  /// Queues a report locally (works offline) and sends it right away when possible.
  /// Diagnostics are attached so the office does not have to ask "which version? did it sync?".
  /// Returns true if it reached the server now, false if it waits for the next sync.
  Future<bool> reportIssue({required String category, required String message, String? collectionId}) async {
    final queue = await _issueQueue();
    queue.add({
      'client_uuid': const Uuid().v4(),
      'category': category,
      'message': message,
      if (collectionId != null) 'collection_id': collectionId,
      'context': {
        'app': 'mobile',
        'app_version': appVersion,
        'device_id': deviceId,
        'online': online,
        'pending_collections': pendingCount,
        'producers_on_phone': producerCount,
        'last_sync_at': lastSyncAt?.toIso8601String(),
        'last_sync_error': lastSyncError,
        'reported_at': DateTime.now().toUtc().toIso8601String(),
      },
    });
    await db.set('issue_queue', jsonEncode(queue));
    pendingIssues = queue.length;
    notifyListeners();
    if (!online) return false;
    await _sendIssues();
    return pendingIssues == 0;
  }

  Future<void> _sendIssues() async {
    final queue = await _issueQueue();
    final left = <Map<String, dynamic>>[];
    for (final issue in queue) {
      try {
        await api.postIssue(issue, deviceId);
      } on ApiException catch (e) {
        // Only a report the server calls invalid (400/422, e.g. unknown collection) is dropped. Network errors,
        // an expired session or a server error keep it queued; client_uuid makes the retry idempotent.
        if (e.status != 400 && e.status != 422) left.add(issue);
      }
    }
    await db.set('issue_queue', jsonEncode(left));
    pendingIssues = left.length;
    notifyListeners();
  }

  // ---------------------------------------------------------------- sync

  /// Push first (the collector's work is what matters), then pull reference data and statuses.
  /// `auto` syncs (new entry, network back, timer) respect the failure backoff and pull at most every
  /// 15 minutes; manual syncs always do both. Returns a short French summary for a snackbar.
  Future<String> sync({bool full = false, bool auto = false}) async {
    if (syncing || !loggedIn) return '';
    if (auto && _nextAutoAttempt != null && DateTime.now().isBefore(_nextAutoAttempt!)) return '';
    syncing = true;
    lastSyncError = null;
    notifyListeners();
    var sent = 0, rejected = 0;
    try {
      final pending = await db.pending();
      for (var i = 0; i < pending.length; i += _pushBatch) {
        final chunk = pending.sublist(i, i + _pushBatch > pending.length ? pending.length : i + _pushBatch);
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

      if (pendingIssues > 0) await _sendIssues();

      final pullDue = !auto || full || _lastPullAt == null || DateTime.now().difference(_lastPullAt!) > _autoPullEvery;
      if (pullDue) {
        final cursor = full ? null : await db.get('cursor');
        final ref = full ? null : await db.get('ref_hash');
        final data = await api.pull(cursor, ref, deviceId);
        await db.upsertProducers((data['producers'] as List).cast<Map<String, dynamic>>());
        await db.applyServerStatuses((data['collections'] as List).cast<Map<String, dynamic>>());
        // null = unchanged since our `ref_hash`: keep the local copy, nothing was downloaded
        if (data['prices'] != null) await db.replacePrices((data['prices'] as List).cast<Map<String, dynamic>>());
        final settings = data['settings'] as Map<String, dynamic>?;
        if (settings != null) {
          await db.set('max_moisture', settings['max_moisture_percent'].toString());
          await db.set('max_weight', settings['max_weight_kg'].toString());
        }
        await db.set('ref_hash', data['ref_hash'] as String);
        await db.set('cursor', data['cursor'] as String);
        _lastPullAt = DateTime.now();
      }
      await db.set('last_sync_at', DateTime.now().toUtc().toIso8601String());
      _failures = 0;
      _nextAutoAttempt = null;
    } on ApiException catch (e) {
      lastSyncError = e.message;
      if (e.isNetwork) {
        _failures++;
        final minutes = [1, 2, 4, 8, 16, 30][(_failures - 1).clamp(0, 5)];
        _nextAutoAttempt = DateTime.now().add(Duration(minutes: minutes));
      }
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
