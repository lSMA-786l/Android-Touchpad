import 'package:flutter/foundation.dart';
import 'package:tray_manager/tray_manager.dart';
import 'package:window_manager/window_manager.dart';

/// System-tray integration: icon, tooltip, menu, click-to-show.
class TrayService with TrayListener {
  TrayService._();

  static Future<void> init() async {
    final svc = TrayService._();
    await trayManager.setIcon('assets/tray_icon.png');
    await trayManager.setToolTip('TPad Receiver');
    await trayManager.setContextMenu(
      Menu(items: [
        MenuItem(key: 'show', label: 'Show TPad Receiver'),
        MenuItem.separator(),
        MenuItem(key: 'quit', label: 'Quit'),
      ]),
    );
    trayManager.addListener(svc);
    debugPrint('tray initialized');
  }

  @override
  void onTrayIconMouseDown() {
    windowManager.show();
    windowManager.focus();
  }

  @override
  void onTrayMenuItemClick(MenuItem menuItem) {
    switch (menuItem.key) {
      case 'show':
        windowManager.show();
        windowManager.focus();
      case 'quit':
        windowManager.close();
    }
  }
}
