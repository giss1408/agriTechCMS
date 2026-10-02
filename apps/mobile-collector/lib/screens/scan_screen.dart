import 'package:flutter/material.dart';
import 'package:mobile_scanner/mobile_scanner.dart';

import '../data/app_state.dart';
import '../logic.dart';

/// Scans the producer's QR card and resolves it against the local copy (works offline).
class ScanScreen extends StatefulWidget {
  const ScanScreen({super.key, required this.state});
  final AppState state;

  @override
  State<ScanScreen> createState() => _ScanScreenState();
}

class _ScanScreenState extends State<ScanScreen> {
  final _controller = MobileScannerController(formats: const [BarcodeFormat.qrCode]);
  bool _handled = false;
  String? _message;

  Future<void> _onDetect(BarcodeCapture capture) async {
    if (_handled) return;
    final raw = capture.barcodes.firstOrNull?.rawValue;
    if (raw == null) return;
    final parsed = parseProducerQr(raw);
    if (parsed == null) {
      setState(() => _message = 'Ce QR code n\'est pas une carte producteur');
      return;
    }
    _handled = true;
    final producer = await widget.state.db.producer(parsed.id);
    if (!mounted) return;
    if (producer == null) {
      _handled = false;
      setState(() => _message = 'Producteur ${parsed.code} inconnu sur ce téléphone : synchronisez puis réessayez');
      return;
    }
    Navigator.of(context).pop(producer);
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Scanner la carte'),
        actions: [IconButton(icon: const Icon(Icons.flashlight_on), onPressed: _controller.toggleTorch, tooltip: 'Lampe')],
      ),
      body: Stack(children: [
        MobileScanner(controller: _controller, onDetect: _onDetect),
        Center(
          child: Container(
            width: 240,
            height: 240,
            decoration: BoxDecoration(border: Border.all(color: Colors.white, width: 3), borderRadius: BorderRadius.circular(16)),
          ),
        ),
        if (_message != null)
          Positioned(
            left: 16,
            right: 16,
            bottom: 32,
            child: Card(child: Padding(padding: const EdgeInsets.all(16), child: Text(_message!, textAlign: TextAlign.center))),
          ),
      ]),
    );
  }
}
