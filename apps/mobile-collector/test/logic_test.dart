import 'package:cabosse_collecte/logic.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('QR card', () {
    test('parses a producer card', () {
      final r = parseProducerQr('AGT1:prod_01abc:DAL-00042');
      expect(r?.id, 'prod_01abc');
      expect(r?.code, 'DAL-00042');
    });
    test('rejects anything else', () {
      expect(parseProducerQr('https://example.com'), isNull);
      expect(parseProducerQr('AGT1:usr_x:DAL-1'), isNull);
    });
  });

  test('decimal input accepts French comma', () {
    expect(parseDecimal('120,5'), 120.5);
    expect(parseDecimal(' 80 '), 80);
    expect(parseDecimal('12,345'), isNull);
    expect(parseDecimal('abc'), isNull);
  });

  test('price on a date follows the same rule as the server', () {
    final prices = [
      PriceRow(product: 'cacao', quality: 'A', pricePerKg: 2200, effectiveFrom: DateTime.utc(2026, 4, 1), effectiveTo: DateTime.utc(2026, 9, 30)),
      PriceRow(product: 'cacao', quality: 'A', pricePerKg: 2800, effectiveFrom: DateTime.utc(2026, 10, 1)),
    ];
    expect(priceOn(prices, 'cacao', 'A', DateTime.utc(2026, 9, 30, 23))?.pricePerKg, 2200);
    expect(priceOn(prices, 'cacao', 'A', DateTime.utc(2026, 10, 1, 6))?.pricePerKg, 2800);
    expect(priceOn(prices, 'cacao', 'B', DateTime.utc(2026, 10, 1)), isNull);
    expect(estimateAmount(120.5, 2800), 337400);
  });

  test('formats FCFA with narrow spaces', () {
    expect(fcfa(1920000), '1 920 000 F');
  });

  test('normalises Ivorian numbers', () {
    expect(normalizeIvorianPhone('07 00 00 00 02'), '+2250700000002');
    expect(normalizeIvorianPhone('+225 05 12 34 56 78'), '+2250512345678');
    expect(normalizeIvorianPhone('12345'), isNull);
  });
}
