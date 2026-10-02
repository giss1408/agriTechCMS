import 'package:flutter/material.dart';

import '../data/app_state.dart';
import '../data/models.dart';
import 'collection_form_screen.dart';
import 'scan_screen.dart';
import 'today_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key, required this.state});
  final AppState state;

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int _todayCount = 0;

  AppState get state => widget.state;

  @override
  void initState() {
    super.initState();
    state.addListener(_refreshToday);
    _refreshToday();
  }

  @override
  void dispose() {
    state.removeListener(_refreshToday);
    super.dispose();
  }

  Future<void> _refreshToday() async {
    final now = DateTime.now();
    final rows = await state.db.since(DateTime(now.year, now.month, now.day));
    if (mounted) setState(() => _todayCount = rows.length);
  }

  Future<void> _sync() async {
    final msg = await state.sync();
    if (mounted && msg.isNotEmpty) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(msg)));
  }

  Future<void> _newCollection({LocalProducer? producer}) async {
    final saved = await Navigator.of(context).push<bool>(
      MaterialPageRoute(builder: (_) => CollectionFormScreen(state: state, initialProducer: producer)),
    );
    if (saved == true && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(state.online ? 'Collecte enregistrée — envoi en cours' : 'Collecte enregistrée sur le téléphone')),
      );
    }
  }

  Future<void> _scan() async {
    final producer = await Navigator.of(context).push<LocalProducer>(MaterialPageRoute(builder: (_) => ScanScreen(state: state)));
    if (producer != null) await _newCollection(producer: producer);
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return ListenableBuilder(
      listenable: state,
      builder: (context, _) => Scaffold(
        appBar: AppBar(
          title: Text(state.cooperativeName.isEmpty ? 'Cabosse Collecte' : state.cooperativeName, overflow: TextOverflow.ellipsis),
          actions: [
            PopupMenuButton<String>(
              onSelected: (v) async {
                if (v == 'full') {
                  final msg = await state.sync(full: true);
                  if (context.mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(msg)));
                }
                if (v == 'logout') await state.logout();
              },
              itemBuilder: (_) => const [
                PopupMenuItem(value: 'full', child: Text('Tout re-télécharger')),
                PopupMenuItem(value: 'logout', child: Text('Se déconnecter')),
              ],
            ),
          ],
        ),
        body: RefreshIndicator(
          onRefresh: _sync,
          child: ListView(
            padding: const EdgeInsets.all(16),
            children: [
              Text('Bonjour ${state.greetingName}', style: theme.textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.bold)),
              const SizedBox(height: 12),
              _SyncCard(state: state, onSync: _sync),
              const SizedBox(height: 20),
              FilledButton.icon(onPressed: _scan, icon: const Icon(Icons.qr_code_scanner, size: 28), label: const Text('Scanner la carte producteur')),
              const SizedBox(height: 12),
              OutlinedButton.icon(onPressed: () => _newCollection(), icon: const Icon(Icons.add), label: const Text('Nouvelle collecte (recherche)')),
              const SizedBox(height: 12),
              OutlinedButton.icon(
                onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => TodayScreen(state: state))),
                icon: const Icon(Icons.list_alt),
                label: Text('Mes collectes du jour : $_todayCount'),
              ),
              const SizedBox(height: 24),
              Text('${state.producerCount} producteurs disponibles hors-ligne', textAlign: TextAlign.center, style: theme.textTheme.bodySmall),
            ],
          ),
        ),
      ),
    );
  }
}

class _SyncCard extends StatelessWidget {
  const _SyncCard({required this.state, required this.onSync});
  final AppState state;
  final VoidCallback onSync;

  @override
  Widget build(BuildContext context) {
    final online = state.online;
    final color = online ? const Color(0xFF2F7A3E) : const Color(0xFFB26B00);
    final last = state.lastSyncAt;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(children: [
              Icon(Icons.circle, size: 14, color: color),
              const SizedBox(width: 8),
              Text(online ? 'Connecté' : 'Hors-ligne', style: TextStyle(color: color, fontWeight: FontWeight.bold, fontSize: 16)),
              const Spacer(),
              if (state.syncing)
                const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2))
              else
                TextButton.icon(onPressed: online ? onSync : null, icon: const Icon(Icons.sync), label: const Text('Synchroniser')),
            ]),
            const SizedBox(height: 8),
            Text(
              state.pendingCount == 0 ? 'Tout est envoyé ✓' : '${state.pendingCount} collecte(s) en attente d\'envoi',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            if (last != null) Text('Dernière synchro : ${_hhmm(last)}', style: Theme.of(context).textTheme.bodySmall),
            if (state.lastSyncError != null)
              Text(state.lastSyncError!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
          ],
        ),
      ),
    );
  }

  static String _hhmm(DateTime t) {
    final l = t.toLocal();
    final now = DateTime.now();
    final time = '${l.hour.toString().padLeft(2, '0')}:${l.minute.toString().padLeft(2, '0')}';
    return l.day == now.day && l.month == now.month ? 'aujourd\'hui à $time' : '${l.day}/${l.month} à $time';
  }
}
