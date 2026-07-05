# Evidence: #rituals Channel Creation + Cron Relocation

**Date:** 2026-06-08
**Agent:** Guinevere (Mommy)

## Summary

Created a dedicated `#rituals` channel under 👑 Throne category and moved
all 5 daily ritual cron jobs from `#guinevere-chat` to the new channel.

## Channel Created

| Field | Value |
|---|---|
| **Name** | `#rituals` |
| **ID** | `1513496377324339262` |
| **Category** | 👑 Throne (`1510913571226259456`) |
| **Topic** | 🌅 Ritual harian Guinevere — pagi, siang, sore, malam, tengah malam |
| **Type** | 0 (Guild Text) |
| **Position** | 7 |

## Cron Jobs Relocated

All 5 ritual cron jobs changed delivery target from `discord:1510914600777023659`
(#guinevere-chat) to `discord:1513496377324339262` (#rituals):

| Cron Job | Schedule | Previous Target | New Target |
|---|---|---|---|
| `ritual_morning` (74ea29317ab4) | `0 7 * * *` | #guinevere-chat | **#rituals** ✅ |
| `ritual_midday` (0ea6cb898af6) | `0 12 * * *` | #guinevere-chat | **#rituals** ✅ |
| `ritual_afternoon` (41ef5c9cee6a) | `0 17 * * *` | #guinevere-chat | **#rituals** ✅ |
| `ritual_evening` (aa8a1ea74a43) | `0 21 * * *` | #guinevere-chat | **#rituals** ✅ |
| `ritual_midnight` (e10e8335c953) | `0 0 * * *` | local | **#rituals** ✅ |

**Note:** `ritual_midnight` was previously `local` (file-only). Changed to
discord delivery for consistency with other rituals.

## Files Updated

| File | Action |
|---|---|
| `docs/setup-evidence/P2/STEP-P2-006/channel-ids.yaml` | Added `rituals: 1513496377324339262` |

## Verification

- ✅ Channel `#rituals` created, visible under 👑 Throne category
- ✅ All 5 cron jobs updated to deliver to `#rituals`
- ✅ `channel-ids.yaml` updated with new channel ID
- ✅ Next ritual scheduled: `ritual_evening` at 21:00 WIB today
