import 'package:flutter/foundation.dart';

/// Timestamped, capped in-memory log shown on the Log tab.
class LogService extends ChangeNotifier {
  static const int _cap = 300;
  final List<String> _lines = [];

  List<String> get lines => List.unmodifiable(_lines);

  void add(String message) {
    final ts = DateTime.now();
    final stamp = '${ts.hour.toString().padLeft(2, '0')}:'
        '${ts.minute.toString().padLeft(2, '0')}:'
        '${ts.second.toString().padLeft(2, '0')}';
    _lines.add('[$stamp] $message');
    if (_lines.length > _cap) {
      _lines.removeRange(0, _lines.length - _cap);
    }
    notifyListeners();
  }

  void clear() {
    _lines.clear();
    notifyListeners();
  }
}
