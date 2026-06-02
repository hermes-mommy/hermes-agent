// hmac-sign.js
// Tasker JavaScriptlet for HMAC-SHA256 signing
// Used by Guinevere surveillance event collection profiles
// Requires: Tasker 5.8+, Java bridge access enabled
// No external dependencies (no CryptoJS, no CDN imports)

// --- Helper: Build Event Payload ---
function buildEventPayload(eventType, deviceId, payload) {
    var occurredAt = new Date().toISOString();
    var event = {
        event_type: eventType,
        device_id: deviceId,
        occurred_at: occurredAt,
        payload: payload
    };
    return JSON.stringify(event);
}

// --- Main Signing Logic ---
try {
    // Read inputs from Tasker variables
    var hmacSecret = java.lang.String("%HMAC_SECRET");
    var body = java.lang.String("%hmac_body");

    // Generate timestamp (Unix epoch seconds)
    var timestamp = Math.floor(Date.now() / 1000).toString();

    // Generate nonce (UUID v4)
    var nonce = java.util.UUID.randomUUID().toString();

    // Build signing string: method:path:timestamp:nonce:body
    var method = "POST";
    var path = "/surveillance/events";
    var signingString = method + ":" + path + ":" + timestamp + ":" + nonce + ":" + body.toString();

    // HMAC-SHA256 via Tasker Java bridge
    var Mac = java.lang.Class.forName("javax.crypto.Mac").newInstance();
    var SecretKeySpec = java.lang.Class.forName("javax.crypto.spec.SecretKeySpec");
    var algorithm = "HmacSHA256";

    var keySpec = new SecretKeySpec(
        java.lang.String(hmacSecret).getBytes("UTF-8"),
        algorithm
    );
    Mac.init(keySpec);

    var rawHmac = Mac.doFinal(
        java.lang.String(signingString).getBytes("UTF-8")
    );

    // Convert byte array to lowercase hex string
    var hexString = "";
    for (var i = 0; i < rawHmac.length; i++) {
        hexString += java.lang.String.format("%02x", rawHmac[i]);
    }

    // Set output variables for Tasker
    setLocal("hmac_signature", hexString);
    setLocal("hmac_timestamp", timestamp);
    setLocal("hmac_nonce", nonce);
    setLocal("hmac_error", "false");

} catch (e) {
    // Set error flag so downstream actions can check
    setLocal("hmac_error", "true");
    setLocal("hmac_signature", "");
    setLocal("hmac_timestamp", "");
    setLocal("hmac_nonce", "");
}
