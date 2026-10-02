/// Closed action set for the TPad protocol.
///
/// The receiver ONLY executes the message types listed here. There is
/// deliberately NO "run arbitrary command" action — see PROTOCOL.md §6.
library;

/// Message type tags for the TCP control channel.
class MsgType {
  MsgType._();
  static const hello = 'hello';
  static const helloAck = 'hello_ack';
  static const pairRequest = 'pair_request';
  static const pairConfirm = 'pair_confirm';
  static const click = 'click';
  static const key = 'key';
  static const macroFire = 'macro_fire';
  static const media = 'media';
  static const presenter = 'presenter';
  static const ping = 'ping';
  static const pong = 'pong';
  static const error = 'error';
}

/// Mouse buttons for [MsgType.click] (`data.button`).
class MouseButton {
  MouseButton._();
  static const left = 'left';
  static const right = 'right';
  static const middle = 'middle';
}

/// Click actions for [MsgType.click] (`data.action`).
class ClickAction {
  ClickAction._();
  static const down = 'down';
  static const up = 'up';

  /// Atomic down+up, for taps.
  static const tap = 'tap';
}

/// Media commands for [MsgType.media] (`data.command`).
class MediaCmd {
  MediaCmd._();
  static const playPause = 'play_pause';
  static const next = 'next';
  static const prev = 'prev';
  static const volUp = 'vol_up';
  static const volDown = 'vol_down';
  static const mute = 'mute';
}

/// Presenter commands for [MsgType.presenter] (`data.command`).
class PresenterCmd {
  PresenterCmd._();
  static const next = 'next';
  static const prev = 'prev';
  static const blank = 'blank';
}

/// Key actions for [MsgType.key] (`data.action`).
/// `data.vk` is a Windows virtual-key code (int).
class KeyAction {
  KeyAction._();
  static const down = 'down';
  static const up = 'up';
  static const press = 'press';
}

/// Error codes for [MsgType.error] (`data.code`).
class ErrorCode {
  ErrorCode._();
  static const badToken = 'bad_token';
  static const badPin = 'bad_pin';
  static const replay = 'replay';
  static const rateLimited = 'rate_limited';
  static const unknownType = 'unknown_type';
  static const unsupportedProtocol = 'unsupported_protocol';
  static const badFrame = 'bad_frame';
}
