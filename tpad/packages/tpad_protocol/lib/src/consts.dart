/// Shared constants for the TPad protocol v1.
library;

/// Protocol version negotiated in `hello`.
const int kProtocolVersion = 1;

/// TCP control channel (TLS) port.
const int kTcpPort = 47900;

/// UDP pointer-stream port.
const int kUdpPort = 47901;

/// mDNS service name advertised by the receiver (optional discovery).
const String kMdnsService = '_tpad._tcp';

/// How long a pairing PIN stays valid (seconds).
const int kPairPinTtlSeconds = 120;

/// Max failed PIN attempts before the PIN is regenerated.
const int kPairPinMaxAttempts = 3;

/// Largest TCP frame the receiver will accept (bytes). Bigger -> dropped.
const int kMaxTcpFrameBytes = 4 * 1024 * 1024;

/// Keepalive ping interval (seconds) and silence timeout (seconds).
const int kKeepaliveSeconds = 15;
const int kSilenceTimeoutSeconds = 45;

/// Max UDP pointer packets per second accepted from one device.
const int kMaxUdpPerSecond = 240;

/// Max TCP control messages per second accepted from one device.
const int kMaxTcpPerSecond = 60;

/// Max allowed |now - ts| on a control message envelope (milliseconds).
const int kMaxClockSkewMs = 60000;
