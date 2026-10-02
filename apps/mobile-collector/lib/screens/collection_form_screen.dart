import 'dart:async';

import 'package:flutter/material.dart';
import 'package:geolocator/geolocator.dart';
import 'package:uuid/uuid.dart';

import '../data/app_state.dart';
import '../data/models.dart';
import '../logic.dart';
import 'producer_search_screen.dart';
import 'scan_screen.dart';

/// The most used screen of the product: must take under 60 seconds, one-handed, offline.
class CollectionFormScreen extends StatefulWidget {
  const CollectionFormScreen({super.key, required this.state, this.initialProducer, this.editing});
  final AppState state;
  final LocalProducer? initialProducer;
  final LocalCollection? editing; // correcting a pending or rejected entry

  @override
  State<CollectionFormScreen> createState() => _CollectionFormScreenState();
}

class _CollectionFormScreenState extends State<CollectionFormScreen> {
  final _weight = TextEditingController();
  final _moisture = TextEditingController();
  final _notes = TextEditingController();
  LocalProducer? _producer;
  String _quality = 'A';
  List<PriceRow> _prices = [];
  Position? _position;
  bool _saving = false;

  AppState get state => widget.state;

  @override
  void initState() {
    super.initState();
    _producer = widget.initialProducer;
    final e = widget.editing;
    if (e != null) {
      _quality = e.quality;
      _weight.text = e.weightKg.toString().replaceAll('.', ',');
      _moisture.text = e.moisturePercent?.toString().replaceAll('.', ',') ?? '';
      _notes.text = e.notes ?? '';
      state.db.producer(e.producerId).then((p) => setState(() => _producer = p));
    }
    state.db.prices().then((p) => setState(() => _prices = p));
    _locate();
    _weight.addListener(() => setState(() {}));
    _moisture.addListener(() => setState(() {}));
  }

  /// GPS is best-effort: a delivery is never blocked because the phone cannot get a fix.
  Future<void> _locate() async {
    try {
      var perm = await Geolocator.checkPermission();
      if (perm == LocationPermission.denied) perm = await Geolocator.requestPermission();
      if (perm == LocationPermission.denied || perm == LocationPermission.deniedForever) return;
      final last = await Geolocator.getLastKnownPosition();
      if (last != null && mounted) setState(() => _position = last);
      final fresh = await Geolocator.getCurrentPosition(
        locationSettings: const LocationSettings(accuracy: LocationAccuracy.high, timeLimit: Duration(seconds: 15)),
      );
      if (mounted) setState(() => _position = fresh);
    } catch (_) {
      // no fix (indoors, GPS off): keep whatever we had
    }
  }

  double? get _weightValue => parseDecimal(_weight.text);
  double? get _moistureValue => _moisture.text.trim().isEmpty ? null : parseDecimal(_moisture.text);

  String? get _weightError {
    if (_weight.text.isEmpty) return null;
    final w = _weightValue;
    if (w == null || w <= 0) return 'Poids invalide';
    if (w > state.maxWeight) return 'Maximum ${state.maxWeight.toStringAsFixed(0)} kg par pesée';
    return null;
  }

  String? get _moistureError {
    if (_moisture.text.trim().isEmpty) return null;
    final m = _moistureValue;
    if (m == null) return 'Valeur invalide';
    if (m > state.maxMoisture) return 'Trop humide (max ${state.maxMoisture} %) : à re-sécher';
    return null;
  }

  PriceRow? get _price => priceOn(_prices, 'cacao', _quality, widget.editing?.collectedAt ?? DateTime.now());

  bool get _canSave => _producer != null && _weightValue != null && _weightError == null && _moistureError == null && !_saving;

  Future<void> _pickProducer({bool scan = false}) async {
    final p = await Navigator.of(context).push<LocalProducer>(
      MaterialPageRoute(builder: (_) => scan ? ScanScreen(state: state) : ProducerSearchScreen(state: state)),
    );
    if (p != null) setState(() => _producer = p);
  }

  Future<void> _save() async {
    setState(() => _saving = true);
    final p = _producer!;
    final price = _price;
    final e = widget.editing;
    await state.record(LocalCollection(
      clientUuid: e?.clientUuid ?? const Uuid().v4(),
      producerId: p.id,
      producerName: p.fullName,
      producerCode: p.code,
      product: 'cacao',
      quality: _quality,
      weightKg: _weightValue!,
      moisturePercent: _moistureValue,
      collectedAt: e?.collectedAt ?? DateTime.now().toUtc(),
      gpsLat: _position?.latitude ?? e?.gpsLat,
      gpsLng: _position?.longitude ?? e?.gpsLng,
      notes: _notes.text.trim().isEmpty ? null : _notes.text.trim(),
      estimatedAmount: price == null ? null : estimateAmount(_weightValue!, price.pricePerKg),
    ));
    if (mounted) Navigator.of(context).pop(true);
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final price = _price;
    final w = _weightValue;
    return Scaffold(
      appBar: AppBar(title: Text(widget.editing == null ? 'Nouvelle collecte' : 'Corriger la collecte')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          if (widget.editing?.errorMessage != null)
            Card(
              color: theme.colorScheme.errorContainer,
              child: Padding(padding: const EdgeInsets.all(12), child: Text('Refusée par le serveur : ${widget.editing!.errorMessage}')),
            ),
          Text('Producteur', style: theme.textTheme.titleMedium),
          const SizedBox(height: 8),
          if (_producer != null)
            Card(
              color: theme.colorScheme.primaryContainer,
              child: ListTile(
                leading: const Icon(Icons.check_circle, size: 32),
                title: Text(_producer!.fullName, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
                subtitle: Text('${_producer!.code}${_producer!.zoneName != null ? ' · ${_producer!.zoneName}' : ''}'),
                trailing: IconButton(icon: const Icon(Icons.edit), onPressed: () => _pickProducer(), tooltip: 'Changer'),
              ),
            )
          else
            Row(children: [
              Expanded(child: FilledButton.icon(onPressed: () => _pickProducer(scan: true), icon: const Icon(Icons.qr_code_scanner), label: const Text('Scanner'))),
              const SizedBox(width: 12),
              Expanded(child: OutlinedButton.icon(onPressed: () => _pickProducer(), icon: const Icon(Icons.search), label: const Text('Rechercher'))),
            ]),
          const SizedBox(height: 20),
          TextField(
            controller: _weight,
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
            style: const TextStyle(fontSize: 28, fontWeight: FontWeight.bold),
            decoration: InputDecoration(labelText: 'Poids (kg)', suffixText: 'kg', errorText: _weightError),
          ),
          const SizedBox(height: 20),
          Text('Qualité', style: theme.textTheme.titleMedium),
          const SizedBox(height: 8),
          SegmentedButton<String>(
            segments: const [
              ButtonSegment(value: 'A', label: Text('A', style: TextStyle(fontSize: 20))),
              ButtonSegment(value: 'B', label: Text('B', style: TextStyle(fontSize: 20))),
            ],
            selected: {_quality},
            onSelectionChanged: (s) => setState(() => _quality = s.first),
            style: const ButtonStyle(minimumSize: WidgetStatePropertyAll(Size.fromHeight(52))),
          ),
          const SizedBox(height: 20),
          TextField(
            controller: _moisture,
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
            style: const TextStyle(fontSize: 20),
            decoration: InputDecoration(labelText: 'Humidité (%) — facultatif', suffixText: '%', errorText: _moistureError),
          ),
          const SizedBox(height: 16),
          TextField(controller: _notes, decoration: const InputDecoration(labelText: 'Remarque — facultatif'), maxLines: 2),
          const SizedBox(height: 12),
          Row(children: [
            Icon(_position != null ? Icons.location_on : Icons.location_searching, size: 18, color: theme.hintColor),
            const SizedBox(width: 6),
            Text(_position != null ? 'Position enregistrée (±${_position!.accuracy.round()} m)' : 'Recherche de la position GPS…',
                style: theme.textTheme.bodySmall),
          ]),
          const SizedBox(height: 20),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(children: [
                Text('Montant estimé', style: theme.textTheme.titleSmall),
                Text(
                  w != null && price != null ? fcfa(estimateAmount(w, price.pricePerKg)) : '—',
                  style: theme.textTheme.headlineMedium?.copyWith(fontWeight: FontWeight.bold, color: theme.colorScheme.primary),
                ),
                Text(
                  price == null ? 'Prix inconnu : synchronisez le téléphone' : '${fcfa(price.pricePerKg)} / kg · calcul définitif par la coopérative',
                  style: theme.textTheme.bodySmall,
                  textAlign: TextAlign.center,
                ),
              ]),
            ),
          ),
          const SizedBox(height: 20),
          FilledButton.icon(onPressed: _canSave ? _save : null, icon: const Icon(Icons.check), label: const Text('VALIDER LA PESÉE')),
          const SizedBox(height: 24),
        ],
      ),
    );
  }
}
