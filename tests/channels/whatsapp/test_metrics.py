from src.channels.whatsapp.metrics import (
    DEFAULT_DEVICE,
    WHATSAPP_CONNECTED,
    WHATSAPP_MESSAGES_RECEIVED_TOTAL,
    WHATSAPP_MESSAGES_SENT_TOTAL,
    WHATSAPP_RATE_LIMIT_HITS_TOTAL,
    WHATSAPP_RECONNECT_ATTEMPTS_TOTAL,
    WHATSAPP_RESPONSE_LATENCY_SECONDS,
    WHATSAPP_SESSION_AGE_SECONDS,
    observe_response_latency,
    record_rate_limit_hit,
    record_received,
    record_reconnect_attempt,
    record_sent,
    set_connected,
    set_session_age,
)


def test_metrics_update_and_labels_exist() -> None:
    set_connected(True)
    set_session_age(12.5)
    record_received()
    record_sent()
    record_reconnect_attempt("network_timeout")
    record_rate_limit_hit("minute")
    observe_response_latency(1.2)

    assert WHATSAPP_CONNECTED.labels(device=DEFAULT_DEVICE)._value.get() == 1
    assert WHATSAPP_SESSION_AGE_SECONDS.labels(device=DEFAULT_DEVICE)._value.get() == 12.5
    assert WHATSAPP_MESSAGES_RECEIVED_TOTAL.labels(device=DEFAULT_DEVICE)._value.get() >= 1
    assert WHATSAPP_MESSAGES_SENT_TOTAL.labels(device=DEFAULT_DEVICE)._value.get() >= 1
    assert WHATSAPP_RECONNECT_ATTEMPTS_TOTAL.labels(device=DEFAULT_DEVICE, reason="network_timeout")._value.get() >= 1
    assert WHATSAPP_RATE_LIMIT_HITS_TOTAL.labels(device=DEFAULT_DEVICE, window="minute")._value.get() >= 1
    assert WHATSAPP_RESPONSE_LATENCY_SECONDS.labels(device=DEFAULT_DEVICE)._sum.get() >= 1.2
