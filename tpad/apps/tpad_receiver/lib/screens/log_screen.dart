import 'package:flutter/material.dart';
import 'package:tpad_theme/tpad_theme.dart';

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
                  ? Center(
                      child: Text('No events yet.',
                          style: TPadText.caption.copyWith(
                              color: Theme.of(context)
                                  .colorScheme
                                  .onSurfaceVariant)))
                  : ListView.builder(
                      padding:
                          const EdgeInsets.all(TPadSpacing.sm),
                      itemCount: lines.length,
                      itemBuilder: (context, i) =>
                          TPadLogLine(lines[i]),
                    ),
            ),
            Padding(
              padding: const EdgeInsets.all(TPadSpacing.xs),
              child: TPadButton(
                label: 'Clear',
                icon: Icons.delete_outline,
                type: TPadButtonType.ghost,
                size: TPadButtonSize.sm,
                onPressed: log.clear,
              ),
            ),
          ],
        );
      },
    );
  }
}
