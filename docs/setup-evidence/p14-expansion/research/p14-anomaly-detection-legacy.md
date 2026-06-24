# P14 wearable anomaly detection and composite scoring research

**Date:** 2026-06-18  
**Scope:** Production-quality, battle-tested wearable health anomaly detection and composite scoring patterns, compared against Guinevere P14-009 / P14-010 / P14-011 assumptions.

## Executive summary

The strongest pattern across mature wearables is **personalized baseline + short-term vs long-term comparison + conservative trend framing**. Real products generally avoid hard clinical-style single-point alerts except for clearly abnormal situations and often gate scores on **minimum data quality / warmup / sleep duration**. For wellness scores, the best-supported approach is:

- establish a **personal baseline** over at least **7 nights to 2–3 weeks**, often improving over **~1 month**;
- compare **recent rolling windows** against **longer-term averages** with recent days weighted more heavily;
- treat **single-night spikes as weak signals** and favor **sustained deviations over multiple days**;
- handle missing/stale data by **withholding the score**, **showing degraded confidence**, or **resetting/reattuning baselines** after long gaps;
- keep **SpO2 guidance conservative**: nocturnal averages around **95–100% are generally normal** in consumer wellness contexts, while **sub-90% is more clinically concerning** in medical literature; a **94% trigger can be reasonable as a wellness caution**, but it is not a medical-grade diagnostic threshold by itself.

For composite health indices, the market trend is toward **pillar-based scores** (sleep, recovery/recovery physiology, activity, cardiovascular strain, stress), but the exact weights are usually proprietary. A fixed **Sleep 40 / Cardio 20 / Activity 20 / Recovery 20** split is plausible as a product design choice, but it is **not a common vendor-published pattern**; real products more often use **nonlinear, hidden weighting** and separate explanatory sub-scores.

## What real products do

### 1) Personal baselines and warmup / confidence

**Oura**
- Readiness contributors are based on **personal averages** and can take **up to two weeks** to learn average values.
- “Long-term” in contributor logic refers to data collected over the **past two months**.
- HRV Balance compares the **past 14 days** to a **three-month average**, with recent days weighted more heavily.
- Sleep Balance uses **two weeks** vs baseline, while Sleep on Readiness uses the **past 24 hours**.

**Google Health / Fitbit readiness**
- Requires **7 nights** before the first readiness score.
- Google says wear the device **consistently for a month** to develop a more accurate baseline.
- Readiness uses **HRV, recent sleep, and resting heart rate**.
- RHR trend guidance emphasizes **sustained rise over a few days** rather than one outlier.

**WHOOP**
- Recovery is a daily readiness measure based on **HRV, resting heart rate, sleep performance, and respiratory rate**.
- WHOOP explicitly emphasizes **personal trends** and warns that a **single low reading is not necessarily a cause for alarm**.
- HRV is measured during **deepest sleep** for consistency.

**Garmin**
- Body Battery and HRV Status require **consistent overnight wear for at least ~3 weeks** to establish baseline behavior.
- Training Readiness / sleep-related features depend on **personal baseline comparison** and overnight data; skipping sleep wear degrades utility.

**Implication for P14:**
- A **28-day baseline** is more conservative than several vendors’ minimum warmup windows and is directionally reasonable for product-quality stability.
- However, consumer wearables often expose **confidence/ramp-up** states, not just a binary ready/not-ready gate. If P14 uses 28 days, it should still expose **partial confidence during days 7–27**, not treat the model as fully mature on day 1 or fully useless until day 28.

### 2) Missing data, stale data, and gap handling

Real products usually do **not** silently interpolate indefinitely.

**Observed patterns:**
- **Oura SpO2** only reports after sleep periods **>3 hours**; missing data troubleshooting suggests sensor, fit, battery, airplane mode, and Bluetooth checks.
- **Google Sleep Score** requires **sleep stages**; if not available, no score is produced. Editing sleep logs can invalidate some analyses.
- **Google Readiness** requires consistent sleep wear each night to continue scoring.
- **Garmin** notes that not wearing the watch to sleep means you lose the benefits of sleep-dependent features.
- **WHOOP** frames readiness as daily and uses overnight physiology; the feature depends on usable overnight data.

**Implication for P14:**
- `<=7 day interpolation` is plausible only as a **short-gap smoothing heuristic** for chart continuity, not as a substitute for real sensor coverage.
- `>7 day reset` is consistent with conservative baseline management. A long missing-data gap should **decay confidence sharply** and likely **recompute baseline** rather than backfill as if nothing happened.
- For production quality, missingness should be represented explicitly with states like: `observed`, `smoothed`, `stale`, `insufficient`, `reset_required`.

### 3) Resting / continuous heart-rate anomaly logic

Across Oura, Google, and WHOOP, the strongest pattern is **deviation from personal baseline plus persistence**.

**Oura**
- RHR contributor declines if RHR is about **3–5 BPM higher** than usual; low RHR can also matter.
- Late heart rate stabilization is a readiness penalty; stabilization ideally happens earlier in the night.

**Google Health**
- Sustained rise in RHR over **a few days** is associated with the body working harder to recover or fight illness.
- Sleep score emphasizes continuity, recovery, and sleep quality rather than a single HR cutoff.

**WHOOP**
- Recovery considers RHR along with HRV, sleep, and respiratory rate.
- The product explicitly warns that a **single low HRV reading** should not be overinterpreted.

**Garmin**
- HRV Status and Body Battery are baseline-driven and trend-oriented.

**Implication for P14:**
- A flat `±20% anomaly threshold` is **too blunt** for continuous heart rate in isolation. It may be acceptable as a coarse alert trigger, but real products generally use **metric-specific thresholds** and **multi-day persistence rules**.
- For resting HR, a better pattern is:
  - compute baseline relative change;
  - require **persistence over 2–3 nights / days**;
  - escalate severity only when the deviation is both **large** and **sustained**.
- For continuous heart rate, use **context-aware thresholds** by state:
  - resting/sleep HR vs active HR should not share one threshold;
  - activity-aware anomaly detection should incorporate movement/load, not only absolute BPM.

### 4) SpO2 alert thresholds

Vendor guidance is generally cautious and trend-based.

**Oura**
- Average nocturnal blood oxygen of **95–100% is generally considered normal**.
- High variation can indicate illness, altitude, or breathing issues.
- Oura explicitly says the feature is **not medical** and should not drive medication/workout changes without a clinician.

**Google Health**
- Exposed feature references SpO2 elsewhere, but the readiness/sleep score pages do **not** make SpO2 a hard alert threshold.

**Medical literature**
- Consumer wearable SpO2 can be reasonably accurate in some lab settings, but performance worsens in **hypoxemia**, **motion**, and some populations.
- Clinical literature commonly treats **<90%** as a major concern for hypoxemia screening/acute care decisions.
- In non-medical wearables, **sub-95% during exertion/sleep can be noisy**; COPD and rehabilitation studies caution against direct medical use.

**Implication for P14:**
- `SpO2 <94 critical` is **medically conservative for a wellness product**, but still should be framed as **wellness-critical / review promptly**, not as a diagnosis.
- For a truly conservative consumer system, consider tiers such as:
  - **95–100%** normal/trending;
  - **92–94%** caution / monitor / repeat;
  - **<92%** high concern / repeat and consider clinical follow-up;
  - **<90%** urgent medical attention guidance.
- If P14 keeps `<94 critical`, it should explicitly label it as **non-diagnostic** and ideally require **repeat confirmation across nights** before persistent escalation.

### 5) Sleep scoring dimensions used by real products

**Google Health Sleep Score**
- Main dimensions: **sleep duration, time to sound sleep, sound sleep, restlessness, full awakenings, interruptions**.
- Metrics reflect **falling asleep, continuity, and adequate amount/quality**.
- Thresholding uses a **5-minute** boundary to distinguish awake vs restlessness.

**Oura Sleep Score / Readiness**
- Sleep score and readiness incorporate **sleep quality**, **RHR**, **HRV**, **body temperature**, **recovery index**, **sleep balance**, **sleep regularity**, and **activity balance**.
- Readiness emphasizes recovery/strain balance rather than pure sleep quality.

**Garmin Sleep / Training Readiness**
- Sleep tracks **duration, stages, movement/restlessness, HR, HRV, and sometimes SpO2**.
- Training readiness pulls from **sleep, HRV, recovery/stress, and training history**.

**WHOOP**
- Recovery uses **sleep performance**, **HRV**, **RHR**, and **respiratory rate**.
- WHOOP’s sleep framing is more performance/recovery focused than sleep hygiene focused.

**Implication for P14:**
- A solid sleep pillar should not be just duration. It should at minimum cover:
  - duration vs need,
  - sleep continuity / awakenings,
  - sleep timing/regularity,
  - recovery physiology during sleep (RHR/HRV/respiratory rate),
  - optional SpO2 variation.
- The Google 5-minute wake/restlessness threshold is a useful production pattern for sleep fragmentation handling.

### 6) Recovery metrics and “readiness / body battery” style patterns

**Common recovery features across products:**
- **HRV** as the primary autonomic recovery signal.
- **Resting HR** as a strain/illness proxy.
- **Respiratory rate** as an illness/breathing-change flag.
- **Sleep performance** as the reset period.
- **Stress / body battery / energy** as a daily operational proxy.

**Oura**
- HRV Balance uses **14-day weighted averages** vs **two-month baseline**.
- Recovery Index gives extra credit when low RHR occurs early enough in the night.

**WHOOP**
- Recovery zones: green/yellow/red based on percentage.
- Explicitly says low recovery may reflect **strain, sickness, stress, lack of sleep, alcohol**.
- The score is meant to guide behavior, not diagnose illness.

**Garmin**
- Body Battery is an energy model combining stress, activity, rest, and sleep.
- HRV Status and Training Readiness reflect trend-based recovery, not single-point output.

**Implication for P14:**
- Recovery should be a **trend composite**, not a simple penalty bucket.
- Use **multi-day smoothing** and separate **acute vs chronic** recovery features.
- If anomaly penalties are used, they should be **bounded**, **recover over time**, and **not drown out sleep/cardiovascular physiology** from a single bad night.

## Comparison to Guinevere P14 assumptions

### P14 assumption: 28-day baseline
**Assessment:** Reasonable and conservative. 
- Real products often learn enough in **7 nights to 3 weeks**, with more stable personalization after **~1 month**.
- A 28-day baseline is not out of family, but it should not prevent earlier provisional scoring.

### P14 assumption: <=7 day interpolation
**Assessment:** Plausible only for short continuity smoothing.
- Real systems usually do not pretend missing data is observed.
- Interpolation should be **clearly labeled**, confidence-reduced, and limited to **display continuity**, not primary alerting.

### P14 assumption: >7 day reset
**Assessment:** Good, conservative product hygiene.
- After long gaps, consumer wearables effectively behave as if they need a **fresh baseline re-fit**.
- Resetting avoids stale personalization and hidden drift.

### P14 assumption: ±20% anomaly threshold
**Assessment:** Too coarse if used universally.
- Products use **metric-specific thresholds** and trend logic.
- A single percentage threshold may work as a UI simplification, but not as the core engine for heart rate, HRV, sleep, and SpO2.
- Better: thresholds by metric, state, and persistence window.

### P14 assumption: severity tiers
**Assessment:** Correct and common.
- WHOOP’s green/yellow/red and Google/Oura score bands confirm that **tiered interpretation** is standard.
- Tiers should reflect **confidence + magnitude + persistence**.

### P14 assumption: SpO2 <94 critical
**Assessment:** Conservative but acceptable as a wellness trigger if labeled properly.
- Real consumer documentation uses trend language and normal ranges closer to **95–100%**.
- Medical literature becomes more concerning below **90–92%**, especially with symptoms or sustained readings.
- For consumer use, `<94` can be a “review / caution” threshold, but not a diagnosis.

### P14 assumption: GHI pillar weights Sleep 40 / Cardio 20 / Activity 20 / Recovery 20
**Assessment:** Product-plausible but not vendor-standard.
- Real vendors rarely publish such explicit weights.
- The structure is sensible if Sleep is the largest pillar, but care is needed so recovery physiology is not double-counted under both Sleep and Recovery.
- Consider making the weights **adaptive** or exposing only pillar outputs, then deriving GHI through a calibrated model.

### P14 assumption: warmup handling
**Assessment:** Strongly aligned with market practice.
- Almost every mature wearable has a warmup or personalization ramp.
- This should include a **confidence meter**, not just a hidden backend state.

### P14 assumption: anomaly penalties
**Assessment:** Use cautiously.
- Penalties are useful for compressing many signals into one index.
- But products in the wild lean toward **explanatory contributors** and **gradual trend penalties**, not harsh one-shot deductions.
- Penalize **persistent deviations** more than isolated anomalies.

## Recommended production pattern for Guinevere

1. **Baseline lifecycle**
   - Stage 0: insufficient data.
   - Stage 1: provisional baseline after 7 nights.
   - Stage 2: stable baseline after 21–28 days.
   - Stage 3: rebaseline after >7 day gap or major behavior change.

2. **Confidence model**
   - Confidence should be a first-class output.
   - Reduce confidence with missingness, short sleep, motion artifacts, device off-body time, and stale windows.

3. **Trend-first detection**
   - Use rolling windows for HR, HRV, sleep, and SpO2.
   - Trigger alerts mainly on **persistent elevation/depression**, not single spikes.

4. **Conservative SpO2 handling**
   - Treat 94–95% as borderline caution in wellness.
   - Treat <92% as high concern.
   - Treat <90% as urgent escalation guidance, especially if symptomatic.
   - Never present as medical diagnosis.

5. **Sleep score design**
   - Prefer dimensions aligned with Google/Oura: duration, continuity, awakenings, regularity, recovery physiology.
   - Use a 5-minute wake threshold or equivalent to separate real awakenings from brief restlessness.

6. **Composite GHI design**
   - Keep the index explainable with pillar scores and contributor deltas.
   - Use a saturating penalty function so one bad signal does not obliterate the whole score.
   - Allow confidence-adjusted output and “score suppressed” when data quality is poor.

## Bottom line

P14’s current assumptions are directionally aligned with real wearable behavior on **personal baselining**, **warmup**, **confidence handling**, and **tiered wellness interpretation**. The main correction is to make the system **more trend-based and less threshold-rigid**, especially for heart rate and SpO2. In particular:

- keep the 28-day baseline, but expose provisional confidence earlier;
- keep the 7-day interpolation / reset idea, but only for smoothing, not as a substitute for observation;
- replace one-size-fits-all `±20%` anomaly logic with metric/state-specific and persistence-aware rules;
- keep `<94` as a conservative wellness warning if desired, but reserve medical urgency for lower sustained values and symptoms;
- keep the pillar model, but avoid overconfident fixed weights unless validated against real user data.

## References

- Oura Readiness Score (updated 2026-02-12): https://support.ouraring.com/hc/en-us/articles/360025589793-Readiness-Score
- Oura Readiness Contributors (updated 2026-02-12): https://support.ouraring.com/hc/lv/articles/360057791533-Readiness-Contributors
- Oura Blood Oxygen Sensing (updated 2026-06-16): https://support.ouraring.com/hc/en-us/articles/7328398760851-Blood-Oxygen-Sensing-SpO2
- Google Health readiness score: https://support.google.com/googlehealth/answer/14236710
- Google Health Sleep Score: https://support.google.com/googlehealth/answer/14236513?hl=en
- Garmin Body Battery: https://www.garmin.com/en-US/garmin-technology/health-science/body-battery/
- Garmin HRV Status: https://www.garmin.com/en-US/garmin-technology/health-science/hrv-status/
- WHOOP Recovery (2026-01-30): https://www.whoop.com/us/en/thelocker/how-does-whoop-recovery-work-101/
- WHOOP HRV (2026-01-30): https://www.whoop.com/us/en/thelocker/heart-rate-variability-hrv/
- Consumer wearable SpO2 literature examples: PMC and MDPI hypoxemia validation papers surfaced in 2025–2026 search results.
