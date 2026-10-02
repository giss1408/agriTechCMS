import 'package:path/path.dart' as p;
import 'package:sqflite/sqflite.dart';

import '../logic.dart';
import 'models.dart';

/// Everything the collector needs offline. The `outbox` table is the source of truth for
/// collections recorded on this phone: rows are never deleted once synced, so the day's
/// history survives without network and across logouts.
class LocalDb {
  LocalDb._(this._db);
  final Database _db;

  static Future<LocalDb> open() async {
    final path = p.join(await getDatabasesPath(), 'cabosse.db');
    final db = await openDatabase(path, version: 1, onCreate: (db, _) async {
      await db.execute('''
        CREATE TABLE producers (
          id TEXT PRIMARY KEY, code TEXT NOT NULL, first_name TEXT NOT NULL, last_name TEXT NOT NULL,
          phone TEXT, zone_name TEXT, status TEXT NOT NULL, search TEXT NOT NULL
        )''');
      await db.execute('CREATE INDEX ix_producers_search ON producers(search)');
      await db.execute('''
        CREATE TABLE prices (
          product TEXT NOT NULL, quality TEXT NOT NULL, price_per_kg INTEGER NOT NULL,
          effective_from TEXT NOT NULL, effective_to TEXT
        )''');
      await db.execute('''
        CREATE TABLE outbox (
          client_uuid TEXT PRIMARY KEY, producer_id TEXT NOT NULL, producer_name TEXT NOT NULL,
          producer_code TEXT NOT NULL, product TEXT NOT NULL, quality TEXT NOT NULL,
          weight_kg REAL NOT NULL, moisture_percent REAL, collected_at TEXT NOT NULL,
          gps_lat REAL, gps_lng REAL, notes TEXT,
          sync_state TEXT NOT NULL,               -- pending | synced | rejected
          estimated_amount INTEGER,
          server_id TEXT, reference TEXT, amount INTEGER, unit_price INTEGER, status TEXT,
          error_code TEXT, error_message TEXT
        )''');
      await db.execute('CREATE TABLE kv (key TEXT PRIMARY KEY, value TEXT)');
    });
    return LocalDb._(db);
  }

  // ---------------------------------------------------------------- key/value

  Future<String?> get(String key) async {
    final rows = await _db.query('kv', where: 'key = ?', whereArgs: [key]);
    return rows.isEmpty ? null : rows.first['value'] as String?;
  }

  Future<void> set(String key, String? value) =>
      _db.insert('kv', {'key': key, 'value': value}, conflictAlgorithm: ConflictAlgorithm.replace);

  // ---------------------------------------------------------------- reference data

  Future<void> upsertProducers(List<Map<String, dynamic>> rows) async {
    final batch = _db.batch();
    for (final r in rows) {
      final search = '${r['code']} ${r['last_name']} ${r['first_name']} ${r['phone'] ?? ''}'.toLowerCase();
      batch.insert(
        'producers',
        {
          'id': r['id'],
          'code': r['code'],
          'first_name': r['first_name'],
          'last_name': r['last_name'],
          'phone': r['phone'],
          'zone_name': r['zone_name'],
          'status': r['status'],
          'search': search,
        },
        conflictAlgorithm: ConflictAlgorithm.replace,
      );
    }
    await batch.commit(noResult: true);
  }

  Future<List<LocalProducer>> searchProducers(String query, {int limit = 50}) async {
    final q = query.trim().toLowerCase();
    final rows = await _db.query(
      'producers',
      where: "status = 'active'${q.isEmpty ? '' : ' AND search LIKE ?'}",
      whereArgs: q.isEmpty ? null : ['%$q%'],
      orderBy: 'last_name, first_name',
      limit: limit,
    );
    return rows.map(LocalProducer.fromRow).toList();
  }

  Future<LocalProducer?> producer(String id) async {
    final rows = await _db.query('producers', where: 'id = ?', whereArgs: [id]);
    return rows.isEmpty ? null : LocalProducer.fromRow(rows.first);
  }

  Future<int> producerCount() async =>
      Sqflite.firstIntValue(await _db.rawQuery("SELECT COUNT(*) FROM producers WHERE status = 'active'")) ?? 0;

  Future<void> replacePrices(List<Map<String, dynamic>> rows) async {
    await _db.transaction((txn) async {
      await txn.delete('prices');
      for (final r in rows) {
        await txn.insert('prices', {
          'product': r['product'],
          'quality': r['quality'],
          'price_per_kg': r['price_per_kg'],
          'effective_from': r['effective_from'],
          'effective_to': r['effective_to'],
        });
      }
    });
  }

  Future<List<PriceRow>> prices() async {
    final rows = await _db.query('prices');
    return rows
        .map((r) => PriceRow(
              product: r['product'] as String,
              quality: r['quality'] as String,
              pricePerKg: r['price_per_kg'] as int,
              effectiveFrom: DateTime.parse('${r['effective_from']}T00:00:00Z'),
              effectiveTo: r['effective_to'] == null ? null : DateTime.parse('${r['effective_to']}T00:00:00Z'),
            ))
        .toList();
  }

  // ---------------------------------------------------------------- outbox

  Future<void> saveCollection(LocalCollection c) =>
      _db.insert('outbox', c.toRow(), conflictAlgorithm: ConflictAlgorithm.replace);

  Future<void> deleteCollection(String clientUuid) =>
      _db.delete('outbox', where: "client_uuid = ? AND sync_state != 'synced'", whereArgs: [clientUuid]);

  Future<List<LocalCollection>> pending() async {
    final rows = await _db.query('outbox', where: "sync_state = 'pending'", orderBy: 'collected_at');
    return rows.map(LocalCollection.fromRow).toList();
  }

  Future<int> pendingCount() async =>
      Sqflite.firstIntValue(await _db.rawQuery("SELECT COUNT(*) FROM outbox WHERE sync_state = 'pending'")) ?? 0;

  Future<List<LocalCollection>> since(DateTime from) async {
    final rows = await _db.query('outbox',
        where: 'collected_at >= ?', whereArgs: [from.toUtc().toIso8601String()], orderBy: 'collected_at DESC');
    return rows.map(LocalCollection.fromRow).toList();
  }

  Future<void> markSynced(String clientUuid, Map<String, dynamic> server) => _db.update(
        'outbox',
        {
          'sync_state': 'synced',
          'server_id': server['id'],
          'reference': server['reference'],
          'amount': server['amount'],
          'unit_price': server['unit_price'],
          'status': server['status'],
          'error_code': null,
          'error_message': null,
        },
        where: 'client_uuid = ?',
        whereArgs: [clientUuid],
      );

  Future<void> markRejected(String clientUuid, String code, String message) => _db.update(
        'outbox',
        {'sync_state': 'rejected', 'error_code': code, 'error_message': message},
        where: 'client_uuid = ?',
        whereArgs: [clientUuid],
      );

  /// Status changes made at the office (validated, paid, rejected) flow back to the phone.
  Future<void> applyServerStatuses(List<Map<String, dynamic>> collections) async {
    final batch = _db.batch();
    for (final c in collections) {
      batch.update(
        'outbox',
        {'status': c['status'], 'amount': c['amount'], 'unit_price': c['unit_price'], 'server_id': c['id'], 'reference': c['reference']},
        where: "client_uuid = ? AND sync_state = 'synced'",
        whereArgs: [c['client_uuid']],
      );
    }
    await batch.commit(noResult: true);
  }
}
