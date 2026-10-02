class LocalProducer {
  const LocalProducer({
    required this.id,
    required this.code,
    required this.firstName,
    required this.lastName,
    this.phone,
    this.zoneName,
  });

  factory LocalProducer.fromRow(Map<String, Object?> r) => LocalProducer(
        id: r['id'] as String,
        code: r['code'] as String,
        firstName: r['first_name'] as String,
        lastName: r['last_name'] as String,
        phone: r['phone'] as String?,
        zoneName: r['zone_name'] as String?,
      );

  final String id;
  final String code;
  final String firstName;
  final String lastName;
  final String? phone;
  final String? zoneName;

  String get fullName => '${lastName.toUpperCase()} $firstName';
}

/// A delivery recorded on this phone. `syncState` is about transport (pending/synced/rejected);
/// `status` is the business status decided at the office (pending_validation/validated/paid/rejected).
class LocalCollection {
  LocalCollection({
    required this.clientUuid,
    required this.producerId,
    required this.producerName,
    required this.producerCode,
    required this.product,
    required this.quality,
    required this.weightKg,
    required this.collectedAt,
    this.moisturePercent,
    this.gpsLat,
    this.gpsLng,
    this.notes,
    this.syncState = 'pending',
    this.estimatedAmount,
    this.serverId,
    this.reference,
    this.amount,
    this.unitPrice,
    this.status,
    this.errorCode,
    this.errorMessage,
  });

  factory LocalCollection.fromRow(Map<String, Object?> r) => LocalCollection(
        clientUuid: r['client_uuid'] as String,
        producerId: r['producer_id'] as String,
        producerName: r['producer_name'] as String,
        producerCode: r['producer_code'] as String,
        product: r['product'] as String,
        quality: r['quality'] as String,
        weightKg: (r['weight_kg'] as num).toDouble(),
        moisturePercent: (r['moisture_percent'] as num?)?.toDouble(),
        collectedAt: DateTime.parse(r['collected_at'] as String),
        gpsLat: (r['gps_lat'] as num?)?.toDouble(),
        gpsLng: (r['gps_lng'] as num?)?.toDouble(),
        notes: r['notes'] as String?,
        syncState: r['sync_state'] as String,
        estimatedAmount: r['estimated_amount'] as int?,
        serverId: r['server_id'] as String?,
        reference: r['reference'] as String?,
        amount: r['amount'] as int?,
        unitPrice: r['unit_price'] as int?,
        status: r['status'] as String?,
        errorCode: r['error_code'] as String?,
        errorMessage: r['error_message'] as String?,
      );

  final String clientUuid;
  final String producerId;
  final String producerName;
  final String producerCode;
  final String product;
  final String quality;
  final double weightKg;
  final double? moisturePercent;
  final DateTime collectedAt;
  final double? gpsLat;
  final double? gpsLng;
  final String? notes;
  final String syncState;
  final int? estimatedAmount;
  final String? serverId;
  final String? reference;
  final int? amount;
  final int? unitPrice;
  final String? status;
  final String? errorCode;
  final String? errorMessage;

  bool get editable => syncState != 'synced';

  Map<String, Object?> toRow() => {
        'client_uuid': clientUuid,
        'producer_id': producerId,
        'producer_name': producerName,
        'producer_code': producerCode,
        'product': product,
        'quality': quality,
        'weight_kg': weightKg,
        'moisture_percent': moisturePercent,
        'collected_at': collectedAt.toUtc().toIso8601String(),
        'gps_lat': gpsLat,
        'gps_lng': gpsLng,
        'notes': notes,
        'sync_state': syncState,
        'estimated_amount': estimatedAmount,
        'server_id': serverId,
        'reference': reference,
        'amount': amount,
        'unit_price': unitPrice,
        'status': status,
        'error_code': errorCode,
        'error_message': errorMessage,
      };

  /// Payload for POST /sync/push. Decimals go as strings so the server keeps exact values.
  Map<String, Object?> toApi() => {
        'client_uuid': clientUuid,
        'producer_id': producerId,
        'collected_at': collectedAt.toUtc().toIso8601String(),
        'product': product,
        'quality': quality,
        'weight_kg': weightKg.toStringAsFixed(2),
        'moisture_percent': moisturePercent?.toStringAsFixed(1),
        'notes': notes,
        if (gpsLat != null && gpsLng != null) 'gps': {'lat': gpsLat, 'lng': gpsLng},
      };
}
