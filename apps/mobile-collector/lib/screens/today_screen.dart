import 'package:flutter/material.dart';

import '../data/app_state.dart';
import '../data/models.dart';
import '../logic.dart';
import 'collection_form_screen.dart';
import 'report_screen.dart';

const _statusLabel = {
  'pending_validation': 'À valider au bureau',
  'validated': 'Validée',
  'paid': 'Payée',
  'rejected': 'Rejetée par le bureau',
  'cancelled': 'Annulée',
};

class TodayScreen extends StatefulWidget {
  const TodayScreen({super.key, required this.state});
  final AppState state;

  @override
  State<TodayScreen> createState() => _TodayScreenState();
}

class _TodayScreenState extends State<TodayScreen> {
  List<LocalCollection> _rows = [];

  @override
  void initState() {
    super.initState();
    widget.state.addListener(_load);
    _load();
  }

  @override
  void dispose() {
    widget.state.removeListener(_load);
    super.dispose();
  }

  Future<void> _load() async {
    final now = DateTime.now();
    final rows = await widget.state.db.since(DateTime(now.year, now.month, now.day));
    if (mounted) setState(() => _rows = rows);
  }

  Future<void> _edit(LocalCollection c) async {
    await Navigator.of(context).push(MaterialPageRoute(builder: (_) => CollectionFormScreen(state: widget.state, editing: c)));
    await _load();
  }

  Future<void> _delete(LocalCollection c) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Supprimer cette collecte ?'),
        content: Text('${c.producerName} — ${c.weightKg} kg. Elle n\'a pas encore été envoyée.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Garder')),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Supprimer')),
        ],
      ),
    );
    if (ok == true) await widget.state.discard(c.clientUuid);
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final totalKg = _rows.where((r) => r.syncState != 'rejected').fold<double>(0, (s, r) => s + r.weightKg);
    final totalF = _rows.where((r) => r.syncState != 'rejected').fold<int>(0, (s, r) => s + (r.amount ?? r.estimatedAmount ?? 0));
    return Scaffold(
      appBar: AppBar(title: const Text('Mes collectes du jour')),
      body: Column(children: [
        Container(
          width: double.infinity,
          color: theme.colorScheme.primaryContainer,
          padding: const EdgeInsets.all(16),
          child: Text('${_rows.length} collectes · ${totalKg.toStringAsFixed(1)} kg · ${fcfa(totalF)}',
              style: theme.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold)),
        ),
        Expanded(
          child: _rows.isEmpty
              ? const Center(child: Text('Aucune collecte aujourd\'hui'))
              : ListView.separated(
                  itemCount: _rows.length,
                  separatorBuilder: (_, __) => const Divider(height: 1),
                  itemBuilder: (_, i) {
                    final c = _rows[i];
                    final t = c.collectedAt.toLocal();
                    final (icon, color, label) = switch (c.syncState) {
                      'synced' => (Icons.cloud_done, Colors.green.shade700, _statusLabel[c.status] ?? 'Envoyée'),
                      'rejected' => (Icons.error, theme.colorScheme.error, c.errorMessage ?? 'Refusée'),
                      _ => (Icons.cloud_upload_outlined, Colors.orange.shade800, 'En attente d\'envoi'),
                    };
                    return ListTile(
                      leading: Icon(icon, color: color, size: 30),
                      title: Text('${c.producerName} — ${c.weightKg.toString().replaceAll('.', ',')} kg ${c.quality}'),
                      subtitle: Text('${t.hour.toString().padLeft(2, '0')}:${t.minute.toString().padLeft(2, '0')} · $label', style: TextStyle(color: color)),
                      trailing: Text(fcfa(c.amount ?? c.estimatedAmount ?? 0), style: const TextStyle(fontWeight: FontWeight.w600)),
                      // Sent collections can no longer be edited on the phone: report the error to the office instead.
                      onTap: c.editable
                          ? () => _edit(c)
                          : () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => ReportScreen(state: widget.state, collection: c))),
                      onLongPress: c.editable ? () => _delete(c) : null,
                    );
                  },
                ),
        ),
        if (_rows.any((r) => r.editable))
          const Padding(padding: EdgeInsets.all(12), child: Text('Touchez une collecte non envoyée pour la corriger, appui long pour la supprimer. Une collecte déjà envoyée : touchez-la pour signaler une erreur.', textAlign: TextAlign.center)),
      ]),
    );
  }
}
