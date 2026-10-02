/// Pure functions, no I/O: unit-tested in test/logic_test.dart.
library;

/// Producer cards carry `AGT1:<producer id>:<producer code>` (see backend services/producers.py).
({String id, String code})? parseProducerQr(String raw) {
  final parts = raw.trim().split(':');
  if (parts.length != 3 || parts[0] != 'AGT1' || !parts[1].startsWith('prod_')) return null;
  return (id: parts[1], code: parts[2]);
}

/// Accepts "120", "120,5" (French keypads) and "120.5". Returns null for anything else.
double? parseDecimal(String raw) {
  final s = raw.trim().replaceAll(' ', '').replaceAll(',', '.');
  if (s.isEmpty || !RegExp(r'^\d+(\.\d{1,2})?$').hasMatch(s)) return null;
  return double.parse(s);
}

class PriceRow {
  const PriceRow({
    required this.product,
    required this.quality,
    required this.pricePerKg,
    required this.effectiveFrom,
    this.effectiveTo,
  });

  final String product;
  final String quality;
  final int pricePerKg;
  final DateTime effectiveFrom; // dates only, UTC midnight
  final DateTime? effectiveTo;
}

/// Same rule as the server: the latest price whose period contains the collection date.
PriceRow? priceOn(List<PriceRow> prices, String product, String quality, DateTime when) {
  final day = DateTime.utc(when.toUtc().year, when.toUtc().month, when.toUtc().day);
  PriceRow? best;
  for (final p in prices) {
    if (p.product != product || p.quality != quality) continue;
    if (p.effectiveFrom.isAfter(day)) continue;
    if (p.effectiveTo != null && p.effectiveTo!.isBefore(day)) continue;
    if (best == null || p.effectiveFrom.isAfter(best.effectiveFrom)) best = p;
  }
  return best;
}

/// Estimate shown to the collector. The server recomputes the real amount (round half up).
int estimateAmount(double weightKg, int pricePerKg) => (weightKg * pricePerKg).round();

String fcfa(num amount) {
  final digits = amount.round().toString();
  final buf = StringBuffer();
  for (var i = 0; i < digits.length; i++) {
    if (i > 0 && (digits.length - i) % 3 == 0) buf.write(' ');
    buf.write(digits[i]);
  }
  return '$buf F';
}

/// Normalises what a collector types into +225XXXXXXXXXX (10 local digits since 2021).
String? normalizeIvorianPhone(String raw) {
  var d = raw.replaceAll(RegExp(r'[^\d+]'), '');
  if (d.startsWith('00')) d = '+${d.substring(2)}';
  if (d.startsWith('225') && d.length == 13) d = '+$d';
  if (!d.startsWith('+') && d.length == 10) d = '+225$d';
  return RegExp(r'^\+225\d{10}$').hasMatch(d) ? d : null;
}
