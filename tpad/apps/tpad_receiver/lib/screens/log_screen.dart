import 'package:flutter/material.dart';

import '../app.dart';

class LogScreen extends StatelessWidget {
  const LogScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final log = ReceiverServices.log;
    return ListenableBuilder(
      listenable: log,
      builder: (context, _) {
        final lines = log.lines;
        return Column(
          children: [
            Expanded(
              child: lines.isEmpty
                  ? const Center(child: Text('No events yet.'))
                  : ListView.builder(
                      padding: const EdgeInsets.all(12),
                      itemCount: lines.length,
                      itemBuilder: (context, i) => SelectableText(
                        lines[i],
                        style: const TextStyle(
                            fontFamily: 'monospace', fontSize: 12),
                      ),
                    ),
            ),
            Padding(
              padding: const EdgeInsets.all(8),
              child: TextButton.icon(
                onPressed: log.clear,
                icon: const Icon(Icons.delete_outline),
                label: const Text('Clear'),
              ),
            ),
          ],
        );
      },
    );
  }
}
