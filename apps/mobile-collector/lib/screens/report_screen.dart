import 'package:flutter/material.dart';

import '../data/app_state.dart';
import '../data/models.dart';

const _categories = {
  'app_bug': ('L\'application ne marche pas', Icons.bug_report),
  'sync': ('Les données ne partent pas / manquent', Icons.sync_problem),
  'data_error': ('Erreur de poids, prix ou montant', Icons.scale),
  'payment': ('Problème de paiement d\'un producteur', Icons.payments),
  'account': ('Connexion / compte', Icons.lock),
  'other': ('Autre', Icons.help_outline),
};

/// "Signaler un problème": works offline, the report waits on the phone until the next sync.
class ReportScreen extends StatefulWidget {
  const ReportScreen({super.key, required this.state, this.collection});
  final AppState state;
  final LocalCollection? collection;

  @override
  State<ReportScreen> createState() => _ReportScreenState();
}

class _ReportScreenState extends State<ReportScreen> {
  late String _category = widget.collection != null ? 'data_error' : 'app_bug';
  final _message = TextEditingController();
  bool _sending = false;

  @override
  void initState() {
    super.initState();
    _message.addListener(() => setState(() {}));
  }

  Future<void> _send() async {
    setState(() => _sending = true);
    final sentNow = await widget.state.reportIssue(
      category: _category,
      message: _message.text.trim(),
      collectionId: widget.collection?.serverId,
    );
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(
      content: Text(sentNow ? 'Signalement envoyé à la coopérative. Merci !' : 'Signalement enregistré : il partira à la prochaine connexion.'),
    ));
    Navigator.of(context).pop();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final c = widget.collection;
    return Scaffold(
      appBar: AppBar(title: const Text('Signaler un problème')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          if (c != null)
            Card(
              color: theme.colorScheme.secondaryContainer,
              child: ListTile(
                leading: const Icon(Icons.receipt_long),
                title: Text('${c.producerName} — ${c.weightKg.toString().replaceAll('.', ',')} kg ${c.quality}'),
                subtitle: Text(c.reference ?? 'Collecte'),
              ),
            ),
          const SizedBox(height: 8),
          Text('Quel est le problème ?', style: theme.textTheme.titleMedium),
          ..._categories.entries.map((e) => RadioListTile<String>(
                value: e.key,
                groupValue: _category,
                onChanged: (v) => setState(() => _category = v!),
                title: Text(e.value.$1),
                secondary: Icon(e.value.$2),
              )),
          const SizedBox(height: 8),
          TextField(
            controller: _message,
            maxLines: 5,
            maxLength: 2000,
            decoration: const InputDecoration(labelText: 'Expliquez en quelques mots', hintText: 'Ce que vous faisiez, ce qui s\'est passé'),
          ),
          Text('La version de l\'application et l\'état de la synchronisation sont joints automatiquement.', style: theme.textTheme.bodySmall),
          const SizedBox(height: 16),
          FilledButton.icon(
            onPressed: _message.text.trim().length >= 5 && !_sending ? _send : null,
            icon: const Icon(Icons.send),
            label: const Text('Envoyer'),
          ),
        ],
      ),
    );
  }
}
