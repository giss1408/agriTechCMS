import 'package:flutter/material.dart';

import '../data/api_client.dart';
import '../data/app_state.dart';
import '../logic.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key, required this.state});
  final AppState state;

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _phone = TextEditingController();
  final _code = TextEditingController();
  String? _normalized;
  String? _devCode;
  String? _error;
  bool _busy = false;

  Future<void> _run(Future<void> Function() action) async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await action();
    } on ApiException catch (e) {
      setState(() => _error = e.message);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _sendCode() => _run(() async {
        final phone = normalizeIvorianPhone(_phone.text);
        if (phone == null) throw ApiException(400, 'invalid_phone', 'Numéro invalide (10 chiffres)');
        final dev = await widget.state.requestCode(phone);
        setState(() {
          _normalized = phone;
          _devCode = dev;
        });
      });

  Future<void> _verify() => _run(() => widget.state.login(_normalized!, _code.text.trim()));

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(24),
          children: [
            const SizedBox(height: 40),
            Icon(Icons.eco, size: 64, color: theme.colorScheme.secondary),
            const SizedBox(height: 12),
            Text('Cabosse Collecte', textAlign: TextAlign.center, style: theme.textTheme.headlineMedium?.copyWith(fontWeight: FontWeight.bold)),
            Text('Saisie des pesées, même sans réseau', textAlign: TextAlign.center, style: theme.textTheme.bodyLarge),
            const SizedBox(height: 40),
            if (_normalized == null) ...[
              TextField(
                controller: _phone,
                keyboardType: TextInputType.phone,
                style: const TextStyle(fontSize: 22),
                decoration: const InputDecoration(labelText: 'Votre numéro de téléphone', hintText: '07 00 00 00 02', prefixIcon: Icon(Icons.phone)),
              ),
              const SizedBox(height: 16),
              FilledButton(onPressed: _busy ? null : _sendCode, child: const Text('Recevoir un code par SMS')),
            ] else ...[
              Text('Code envoyé au $_normalized', textAlign: TextAlign.center),
              if (_devCode != null) ...[
                const SizedBox(height: 8),
                Card(
                  color: theme.colorScheme.secondaryContainer,
                  child: Padding(padding: const EdgeInsets.all(12), child: Text('Mode démo — code : $_devCode', textAlign: TextAlign.center)),
                ),
              ],
              const SizedBox(height: 16),
              TextField(
                controller: _code,
                keyboardType: TextInputType.number,
                maxLength: 6,
                autofocus: true,
                textAlign: TextAlign.center,
                style: const TextStyle(fontSize: 28, letterSpacing: 8),
                decoration: const InputDecoration(labelText: 'Code à 6 chiffres', counterText: ''),
              ),
              const SizedBox(height: 16),
              FilledButton(onPressed: _busy ? null : _verify, child: const Text('Se connecter')),
              TextButton(onPressed: () => setState(() => _normalized = null), child: const Text('Changer de numéro')),
            ],
            if (_busy) const Padding(padding: EdgeInsets.all(16), child: Center(child: CircularProgressIndicator())),
            if (_error != null)
              Padding(
                padding: const EdgeInsets.only(top: 16),
                child: Text(_error!, textAlign: TextAlign.center, style: TextStyle(color: theme.colorScheme.error, fontSize: 16)),
              ),
          ],
        ),
      ),
    );
  }
}
