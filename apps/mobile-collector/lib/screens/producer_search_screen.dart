import 'package:flutter/material.dart';

import '../data/app_state.dart';
import '../data/models.dart';

/// Offline search in the producers downloaded at the last sync (name, code or phone).
class ProducerSearchScreen extends StatefulWidget {
  const ProducerSearchScreen({super.key, required this.state});
  final AppState state;

  @override
  State<ProducerSearchScreen> createState() => _ProducerSearchScreenState();
}

class _ProducerSearchScreenState extends State<ProducerSearchScreen> {
  List<LocalProducer> _results = [];

  @override
  void initState() {
    super.initState();
    _search('');
  }

  Future<void> _search(String q) async {
    final rows = await widget.state.db.searchProducers(q);
    if (mounted) setState(() => _results = rows);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Choisir le producteur')),
      body: Column(children: [
        Padding(
          padding: const EdgeInsets.all(12),
          child: TextField(
            autofocus: true,
            onChanged: _search,
            decoration: const InputDecoration(prefixIcon: Icon(Icons.search), hintText: 'Nom, code ou téléphone'),
          ),
        ),
        Expanded(
          child: _results.isEmpty
              ? const Center(child: Text('Aucun producteur. Synchronisez le téléphone.'))
              : ListView.separated(
                  itemCount: _results.length,
                  separatorBuilder: (_, __) => const Divider(height: 1),
                  itemBuilder: (_, i) {
                    final p = _results[i];
                    return ListTile(
                      minVerticalPadding: 14,
                      title: Text(p.fullName, style: const TextStyle(fontWeight: FontWeight.w600)),
                      subtitle: Text([p.code, p.zoneName, p.phone].whereType<String>().join(' · ')),
                      onTap: () => Navigator.of(context).pop(p),
                    );
                  },
                ),
        ),
      ]),
    );
  }
}
