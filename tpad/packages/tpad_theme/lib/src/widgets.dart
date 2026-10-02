import 'package:flutter/material.dart';

import 'spacing.dart';
import 'typography.dart';

/// The 5 core widgets (token layer 03). Everything in both apps is
/// built from these — no one-off styled widgets, no raw hex.

enum TPadButtonType { primary, secondary, ghost }

enum TPadButtonSize { sm, md, lg }

class TPadButton extends StatelessWidget {
  final String label;
  final IconData? icon;
  final VoidCallback? onPressed;
  final TPadButtonType type;
  final TPadButtonSize size;

  const TPadButton({
    super.key,
    required this.label,
    this.icon,
    this.onPressed,
    this.type = TPadButtonType.primary,
    this.size = TPadButtonSize.md,
  });

  @override
  Widget build(BuildContext context) {
    final height = switch (size) {
      TPadButtonSize.sm => 36.0,
      TPadButtonSize.md => 48.0,
      TPadButtonSize.lg => 56.0,
    };
    final hPad = switch (size) {
      TPadButtonSize.sm => 16.0,
      TPadButtonSize.md => 24.0,
      TPadButtonSize.lg => 32.0,
    };
    final style = ButtonStyle(
      minimumSize: WidgetStatePropertyAll(Size(hPad * 2, height)),
      padding: WidgetStatePropertyAll(EdgeInsets.symmetric(horizontal: hPad)),
      shape: WidgetStatePropertyAll(
        RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(TPadRadius.md),
        ),
      ),
      textStyle: const WidgetStatePropertyAll(TPadText.body),
    );
    final child = Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        if (icon != null) ...[
          Icon(icon, size: 20),
          const SizedBox(width: TPadSpacing.xs),
        ],
        Text(label),
      ],
    );
    switch (type) {
      case TPadButtonType.primary:
        return FilledButton(
            onPressed: onPressed, style: style, child: child);
      case TPadButtonType.secondary:
        return OutlinedButton(
            onPressed: onPressed, style: style, child: child);
      case TPadButtonType.ghost:
        return TextButton(
            onPressed: onPressed, style: style, child: child);
    }
  }
}

class TPadCard extends StatelessWidget {
  final Widget child;
  final EdgeInsetsGeometry padding;

  const TPadCard({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(TPadSpacing.md),
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      color: Theme.of(context).colorScheme.surfaceContainerHighest,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(TPadRadius.lg),
      ),
      margin: EdgeInsets.zero,
      child: Padding(padding: padding, child: child),
    );
  }
}

class TPadInput extends StatelessWidget {
  final String? label;
  final String? hint;
  final TextEditingController? controller;
  final bool obscure;
  final TextInputType keyboard;

  const TPadInput({
    super.key,
    this.label,
    this.hint,
    this.controller,
    this.obscure = false,
    this.keyboard = TextInputType.text,
  });

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return TextField(
      controller: controller,
      obscureText: obscure,
      keyboardType: keyboard,
      style: TPadText.body.copyWith(color: scheme.onSurface),
      decoration: InputDecoration(
        labelText: label,
        hintText: hint,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(TPadRadius.md),
        ),
      ),
    );
  }
}

class TPadSectionHeader extends StatelessWidget {
  final String title;

  const TPadSectionHeader(this.title, {super.key});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: TPadSpacing.sm),
      child: Text(
        title.toUpperCase(),
        style: TPadText.caption.copyWith(
          color: Theme.of(context).colorScheme.onSurfaceVariant,
          letterSpacing: 1.2,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }
}

class TPadLogLine extends StatelessWidget {
  final String line;

  const TPadLogLine(this.line, {super.key});

  @override
  Widget build(BuildContext context) {
    return SelectableText(
      line,
      style: TPadText.mono
          .copyWith(color: Theme.of(context).colorScheme.onSurface),
    );
  }
}
