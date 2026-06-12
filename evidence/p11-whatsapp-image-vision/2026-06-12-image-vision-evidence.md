# Evidence: WhatsApp Image / Vision Support

**Date**: 2026-06-12  
**Commit**: `588abb0`  
**Branch**: `main`  
**Phase**: P11 (Post-deployment feature)  
**Verdict**: **PASS**

---

## 1. What Was Done

Added end-to-end image/vision support for WhatsApp messages through Hermes multimodal pipeline:

- **Neonize client**: Store raw E2E Message protobuf in event metadata so `download_any()` can be called downstream
- **Envelope model**: Add `image_bytes` field and `has_image` property to `WhatsAppMessageEnvelope`
- **Adapter**: Download image bytes asynchronously when `media_type == "image"` detected
- **Policy**: Allow image messages through (was previously blocked with "text-only" message)
- **Bridge**: Build OpenAI multimodal content parts (`image_url` + text) when image present, pass list to Hermes
- **Session adapter**: Widen `send_message()` to accept `str | list[dict]`, extract text-only parts for history storage to avoid base64 bloat in Redis
- **None fix**: Handle `None` LLM response → empty string → fallback message instead of sending literal "None"
- **Model switch**: Change WhatsApp model from `ds/deepseek-v4-flash` → `guinevere` (vision-capable on 9router)

## 2. Root Causes Discovered

| Symptom | Root Cause | Fix |
|---|---|---|
| Image blocked with "text-only" response | Policy gate in `_is_media_message()` returns `ack_media` action | Allow image with `has_image` check |
| LLM returned "None" | `result.get("final_response")` returns `None` → `str(None)` = `"None"` → sent literally | Check `if raw_response` before `str()` |
| DeepSeek refused image_url | `ds/deepseek-v4-flash` model doesn't support vision | Switch to `guinevere` (vision-capable combo model) |
| History would bloat with base64 | History append stores full content object | Extract text-only parts when content is a list |

## 3. Files Changed

| File | Change | Lines |
|---|---|---|
| `src/channels/whatsapp/neonize_client.py` | Add `raw_e2e_message` to metadata dict | +1 |
| `src/channels/whatsapp/envelope.py` | Add `image_bytes` field, `has_image` property | +4 |
| `src/channels/whatsapp/adapter.py` | Download image bytes in `_on_whatsapp_event` | +17 |
| `src/channels/whatsapp/policy.py` | Allow image messages through | +3 |
| `src/channels/whatsapp/bridge.py` | `_build_content()` for multimodal parts | +30 |
| `src/hermes/_session_adapter.py` | Widen `content` type, None handling, text-only history | +7 |
| `src/hermes/adapter.py` | Model changed to `guinevere` | +1 |
| `tests/channels/whatsapp/test_image_vision.py` | 14 new tests | +286 |

## 4. Test Results

```bash
uv run pytest tests/channels/whatsapp/ -q
42 passed in 3.59s
```

Coverage by module:
- **Envelope**: `has_image` True/False for image+bytes, image-no-bytes, text-only, non-image media
- **Policy**: Image with bytes allowed; image without bytes → `ack_media`; video → blocked
- **Bridge**: `_build_content()` returns `str` for text, `list[dict]` for image with base64 verification, "Describe this image." default caption
- **Session**: Text passthrough, multimodal extracts text parts, `[image]` fallback, multiple text parts joined

## 5. Live Proof (PID 1236530)

Full end-to-end image vision pipeline verified on live service:

```
whatsapp_message_event       type=image
wa.message.received          inbound, image, byte_length=3
whatsapp_image_downloaded    image_bytes=278259
whatsapp_multimodal_content_built  image_size_bytes=278259, has_caption=true
conversation turn            model=guinevere, provider=9router, msg='[1 image] Tes'
Turn ended: text_response(finish_reason=stop)     response_len=1010
wa.message.processed         outbound, latency_ms=39831
wa.message.sent              outbound, byte_length=1047
```

**Final metrics**:
- `whatsapp_connected{device="faiz"} = 1.0`
- `whatsapp_messages_received_total{device="faiz"} = 1.0`
- `whatsapp_messages_sent_total{device="faiz"} = 2.0`

**Service state**:
- `PID 1236530`, started `Fri 2026-06-12 09:58:50 WIB`
- `ActiveState=active`, `SubState=running`
- `/health`: `status="ready"`, `connection_state="connected"`
- `ReadWritePaths` includes `/home/guinevere/.hermes/logs`

## 6. Non-Blocking Warnings

- `whatsapp_presence_send_failed` — typing indicator JID field missing, cosmetic only
- `RuntimeWarning: coroutine 'init_milestone_state.<locals>._init' was never awaited` — pre-existing Hermes startup race

## 7. Files Deployed to VPS

All 8 files copied to `/home/guinevere/code/guinevere/` via SCP, validated by grep:

```bash
grep -c 'raw_e2e_message' src/channels/whatsapp/neonize_client.py    # 1
grep -c 'image_bytes' src/channels/whatsapp/envelope.py               # 3
grep -c 'download_any' src/channels/whatsapp/adapter.py               # 1
grep -c 'has_image' src/channels/whatsapp/policy.py                   # 1
grep -c 'multimodal' src/channels/whatsapp/bridge.py                  # 1
grep -c 'list\[dict' src/hermes/_session_adapter.py                   # 1
grep -c 'guinevere' src/hermes/adapter.py                             # 1
```

## 8. Acceptance Criteria Mapping

| Criterion | Status |
|---|---|
| Image downloaded from WhatsApp | ✅ 278KB |
| Policy allows image through | ✅ |
| Multimodal content built with base64 | ✅ |
| Hermes receives list content | ✅ |
| Vision-capable model processes image | ✅ guinevere |
| Response sent back to user | ✅ 1047 bytes |
| Text-only history stored (no base64 bloat) | ✅ |
| Non-image media still blocked | ✅ (video → ack_media) |
| Existing text-only path unchanged | ✅ 42/42 tests pass |
| "None" response handled gracefully | ✅ (empty → fallback) |

## 9. Design Decisions

1. **Eager download in adapter** (not lazy in bridge): Simpler, download happens once per message regardless of route.
2. **Text-only history extraction**: Prevents Redis bloat from base64 data. Falls back to `"[image]"` if no text parts.
3. **`guinevere` combo model**: Supports vision + reasoning under one model name. Configured with `supports_vision: true` in Hermes config.
4. **Policy allows only images with bytes**: Image event without downloaded bytes (download failure) still blocked.

## 10. Rollback Plan

- Revert commit `588abb0` to roll back all 8 files
- If only image processing is problematic: revert `adapter.py` + `policy.py` to keep text path intact
- If model regression: revert `src/hermes/adapter.py` to `ds/deepseek-v4-flash`

---

**Verdict: PASS** — All criteria met, live proof confirmed on PID 1236530 with guinevere vision model.
