# P14 wearable anomaly detection and composite scoring research

**Date:** 2026-06-18  
**Scope:** Production-quality wearable health anomaly detection and composite scoring patterns, compared against Guinevere P14-009 / P14-010 / P14-011 assumptions.

## Executive summary

The strongest production pattern across mature wearables is **personal baseline + recent-vs-longer-term trend comparison + conservative confidence gating**. Real consumer products generally avoid claiming that a single reading is meaningful on its own; they lean on **sustained deviations, sleep-anchored measurements, and degraded-confidence states** when data is sparse or stale.

For Guinevere P14, the broad direction is sound:

- **28-day baseline**: conservative and defensible for stable personalization.
- **>7-day gap reset**: appropriate to prevent stale personalization.
- **Tiered severity**: aligned with mainstream wearable UX.
- **Composite score pillars**: plausible product structure.

The main production-quality gaps are:

1. **`±20%` anomaly logic is too blunt if used universally.** Heart rate, HRV, sleep, SpO2, and steps should not share one threshold policy.
2. **Interpolation must not masquerade as observation.** Short-gap smoothing is fine for continuity, but alerting should degrade confidence and avoid treating missing periods as real data.
3. **SpO2 needs explicit wellness framing.** `<94%` is a conservative caution trigger, but not a diagnosis or medical-grade alarm by itself.
4. **GHI should expose confidence and contributors.** A single opaque number is brittle unless it can be explained, suppressed, or downweighted when data quality is weak.
5. **Anomaly penalties should be saturating and persistent, not one-shot.** A single bad signal should not dominate the whole index.

Bottom line: P14 is directionally consistent with real wearable products, but the engine should be made more **trend-based, confidence-aware, and metric-specific** before implementation.

## External best-practice patterns

### 1) Personal baselines and warmup

Common production pattern:

- establish a personal baseline over **7 nights to 2–3 weeks**;
- improve stability over **~1 month**;
- weight recent data more heavily than old data;
- surface a **provisional / learning** state before the baseline is mature.

Observed vendor patterns:

- **Oura**: readiness contributors are based on personal averages and can take around **two weeks** to learn; several contributors compare **14 days** against longer baselines.
- **Google Health / Fitbit**: readiness requires **7 nights** before the first score; Google recommends wearing the device consistently for **about a month** to improve baseline accuracy.
- **WHOOP**: recovery is explicitly trend-based and warns against overreacting to a single low reading.
- **Garmin**: Body Battery / HRV Status depend on consistent overnight wear, with baseline behavior stabilizing after several weeks.

Production implication:

- A **28-day baseline** is reasonable.
- However, the system should still expose **provisional confidence** during the warmup period instead of behaving as if the metric is fully valid or fully invalid.

## 2) Missing data, stale data, and gap handling

Production-quality wearables generally do **not** silently pretend that missing data was observed.

Common patterns:

- suppress or degrade scores when sleep or sensor coverage is insufficient;
- require minimum wear time for certain metrics;
- use explicit states such as `insufficient`, `stale`, `learning`, or `rebaseline`;
- treat long gaps as a reason to **re-fit** the baseline.

Implications for P14:

- `<=7 day interpolation` is acceptable only as **display smoothing** or continuity support.
- `>7 day reset` is a good conservative rule.
- Missingness should be represented explicitly, ideally with states like:
  - `observed`
  - `smoothed`
  - `stale`
  - `insufficient`
  - `reset_required`

This matters because anomaly alerts and GHI outputs become untrustworthy if they are computed from stale or fabricated continuity.

## 3) Heart-rate anomaly thresholds

The strongest real-world pattern is **baseline deviation + persistence + context**.

Production observations:

- resting HR changes of only **3–5 bpm above usual** can matter in readiness systems;
- sustained rises over **multiple days** are more informative than one-off spikes;
- active vs resting vs sleep heart rate should not share one threshold;
- context like motion, training load, fever, or illness should matter.

Implications for P14:

- a flat `±20%` threshold is too coarse for heart-rate analysis if used as the core rule;
- it may be acceptable as a rough coarse trigger, but should be refined into:
  - metric-specific thresholds,
  - state-specific thresholds (resting vs sleep vs activity), and
  - persistence-aware escalation.

Recommended production shape:

- **Resting HR**: compare against baseline, require persistence over **2–3 nights / days**.
- **Continuous HR**: compare within activity state, not only absolute BPM.
- **Sustained elevation**: make that a stronger trigger than a single reading.

## 4) SpO2 alerting

Consumer wearable guidance is generally conservative and trend-oriented.

Observed pattern:

- normal nocturnal oxygen values often sit around **95–100%** in consumer wellness documentation;
- variation matters, not only absolute value;
- medical literature becomes much more concerning below **90–92%**, especially when sustained or symptomatic;
- wearable SpO2 accuracy drops in motion, poor fit, and some populations.

Implications for P14:

- `<94% critical` is **conservative** and acceptable as a **wellness warning**.
- It should **not** be framed as diagnosis.
- If used, it should ideally be paired with repeat confirmation or persistence rules.

A conservative consumer-friendly tiering model would be:

- **95–100%**: normal / monitor
- **92–94%**: caution / repeat / watch trend
- **<92%**: high concern / consider follow-up
- **<90%**: urgent medical attention guidance, especially if symptomatic

P14’s `<94% critical` rule is not obviously wrong, but it is underspecified unless the product language makes clear that it is a **wellness-critical trigger**, not a medical conclusion.

## 5) Sleep scoring dimensions

Real products do not score sleep on duration alone.

Common dimensions across consumer wearables:

- duration;
- continuity / awakenings / restlessness;
- sleep timing / regularity;
- sleep stages;
- sleep physiology during the night, especially HR / HRV / respiratory stability;
- optional SpO2 variation.

Examples:

- **Google Health Sleep Score** uses duration, sound sleep, restlessness, awakenings, and interruptions.
- **Oura** incorporates sleep quality plus recovery-linked signals in readiness.
- **Garmin** tracks duration, stages, movement, HR, HRV, and sometimes SpO2.
- **WHOOP** emphasizes sleep performance as part of recovery.

Implications for P14:

A good sleep pillar should include at least:

1. duration vs need,
2. continuity / awakenings,
3. sleep timing / regularity,
4. recovery physiology during sleep,
5. optional SpO2 variability.

This also means that a sleep score built only from duration and stage percentages is likely incomplete.

## 6) Recovery metrics

The common recovery pattern in production wearables is a composite of:

- **HRV** as autonomic recovery signal,
- **RHR** as strain or illness proxy,
- **respiratory rate** where available,
- **sleep performance** as the nightly reset,
- **stress / energy / readiness** as a trend summary.

Observed vendor behaviors:

- **WHOOP** frames recovery as readiness, not diagnosis.
- **Oura** weighs HRV and RHR trends over multi-day windows.
- **Garmin** Body Battery behaves like an energy budget model, not a medical metric.

Implications for P14:

- Recovery should be a **trend composite**.
- It should not be a penalty bucket that can be wiped out by a single anomaly.
- Penalties should be **bounded** and **recover over time**.

## 7) Composite health index design

Production systems usually prefer one of two patterns:

1. **Explainable pillar model** with visible sub-scores.
2. **Hidden calibrated model** with post-hoc explanations.

For a system like P14, an explainable pillar model is the safer choice.

What production systems tend to do well:

- keep the index interpretable;
- expose pillar scores and contributor deltas;
- suppress or degrade the score when data quality is poor;
- avoid letting one bad input destroy the whole index;
- use nonlinear or saturating penalties.

Implications for P14 GHI:

- The fixed **Sleep 40 / Cardio 20 / Activity 20 / Recovery 20** split is plausible as a product decision.
- It is not a common vendor-published standard.
- It may work, but it should be validated against actual data because recovery physiology can otherwise be double-counted.

A safer production pattern is:

- keep the pillar structure,
- expose each pillar separately,
- use confidence-aware gating,
- apply bounded anomaly penalties,
- make the final GHI suppressible when data quality is poor.

## Comparison against P14-009 / P14-010 / P14-011 assumptions

### P14-009: 28-day baseline computation

**Assessment:** mostly good.

- Directionally aligned with real wearable personalization.
- Conservative enough for stable baselines.
- The baseline should still emit a **confidence / learning state** during warmup.

**Risk:** low to medium.

**What looks underspecified:**

- how sample coverage affects confidence;
- whether weekends / weekdays are weighted;
- whether baselines are per-metric or cross-metric;
- how to treat a metric with enough overall data but sparse recent data.

### P14-009: `<=7 day interpolation`, `>7 day reset`

**Assessment:** good, but only if interpolation is limited.

- Reset after long gaps is production-friendly.
- Interpolation is acceptable only for continuity, not for alerting or pretending sensor coverage exists.

**Risk:** medium if interpolation feeds alerts.

**What looks underspecified:**

- whether interpolation is visual only or algorithmic;
- how confidence decays during gaps;
- whether gap resets are metric-specific.

### P14-010: `±20%` anomaly threshold

**Assessment:** too blunt as a universal rule.

- Works as a UI simplification.
- Does not match production vendor behavior for heart rate, HRV, sleep, or SpO2.
- Real systems are more trend- and state-aware.

**Risk:** high if used as the main engine.

**What looks underspecified:**

- which metrics use percent deviation vs absolute thresholds;
- how to handle metrics with low variance;
- whether activity context suppresses heart-rate alerts;
- whether persistence is required.

### P14-010: severity tiers

**Assessment:** good.

- Tiers are standard and useful.
- Severity should reflect **magnitude + persistence + confidence**.

**Risk:** low.

**What looks underspecified:**

- how special rules override tiers;
- whether severity is per-event or per-window;
- whether multiple weak anomalies can accumulate.

### P14-010: SpO2 <94 critical

**Assessment:** conservative and acceptable only as wellness alerting.

- This is not far from real-world caution language.
- But it should not be presented as medical diagnosis.

**Risk:** medium if wording is too strong.

**What looks underspecified:**

- persistence requirement;
- how many consecutive nights or readings trigger escalation;
- what to do when signal quality is poor.

### P14-011: GHI pillar weights

**Assessment:** product-plausible, not vendor-standard.

- Sleep-weighted composites are common in spirit.
- Vendors usually do not expose a simple fixed formula.

**Risk:** medium.

**What looks underspecified:**

- whether pillars overlap in physiology;
- whether anomaly penalties are bounded;
- how confidence changes the final score;
- whether the score can be withheld entirely on poor data days.

### P14-011: warmup handling

**Assessment:** strong and aligned with market practice.

- Warmup is necessary.
- It should be visible to users / downstream systems.

**Risk:** low.

**What looks underspecified:**

- whether GHI is suppressed or merely lower-confidence before warmup completes;
- whether partial scores are allowed after 7–14 days.

### P14-011: anomaly penalties

**Assessment:** useful, but dangerous if too aggressive.

- Penalties help compress multiple signals into one number.
- Real products tend to use gradual trend penalties and contributor explanations.

**Risk:** medium to high if penalties dominate the score.

**What looks underspecified:**

- penalty cap;
- decay / recovery behavior;
- whether repeated anomalies stack linearly or saturate;
- how penalties interact with confidence.

## What is likely fine vs risky vs underspecified

### Likely fine

- 28-day baseline window.
- >7-day baseline reset.
- Tiered score bands.
- Pillar-based GHI concept.
- Conservative SpO2 caution threshold, if framed correctly.

### Risky

- one-size-fits-all `±20%` anomaly threshold;
- treating interpolation as real observation;
- harsh anomaly penalties that dominate the composite score;
- medical-sounding language around SpO2 alerts;
- scoring everything even when the data is sparse or stale.

### Underspecified

- confidence model and score suppression rules;
- metric-specific alert thresholds;
- persistence requirements for HR / SpO2 anomalies;
- how sleep fragmentation is encoded;
- how recovery physiology is separated from sleep physiology;
- how scores recover after bad days.

## Recommended production pattern for Guinevere

1. **Baseline lifecycle**
   - Stage 0: insufficient data.
   - Stage 1: provisional baseline after about 7 nights.
   - Stage 2: stable baseline after 21–28 days.
   - Stage 3: rebaseline after >7 day gap or major behavior change.

2. **Confidence as a first-class output**
   - Decrease confidence with missingness, short sleep, motion artifacts, and stale windows.
   - Allow score suppression when confidence is too low.

3. **Trend-first detection**
   - Use rolling windows for HR, HRV, sleep, and SpO2.
   - Prioritize sustained deviations over single spikes.

4. **Conservative SpO2 handling**
   - Treat 94–95% as borderline caution in wellness.
   - Treat <92% as high concern.
   - Treat <90% as urgent medical guidance, especially if symptomatic.
   - Never present as diagnosis.

5. **Sleep score design**
   - Include duration, continuity, awakenings, regularity, and recovery physiology.
   - Use a wake/restlessness threshold comparable to production systems.

6. **Composite GHI design**
   - Keep pillar scores visible.
   - Use saturating penalties.
   - Preserve explainability.
   - Suppress or downgrade the score when data quality is poor.

## Practical implementation caveats

- **Cold start:** do not pretend the baseline is mature before enough nights are collected.
- **Missing data:** do not backfill missing sensor time as if it were real.
- **Watch-off-body / bad-fit periods:** these should reduce confidence sharply.
- **Metric heterogeneity:** heart rate, HRV, sleep, activity, and SpO2 need different rules.
- **Alert fatigue:** only persistent or high-confidence events should become alerts.
- **Medical boundaries:** SpO2 and heart-rate alerts in consumer wearables should be phrased as wellness signals, not diagnoses.
- **Score stability:** a composite should not oscillate wildly because of one anomalous night.

## Bottom line

P14’s current assumptions are broadly consistent with what production wearable products do, but the implementation needs more algorithmic nuance to be trustworthy end-to-end.

The most important changes are:

- keep the **28-day baseline**, but surface a real confidence/warmup state;
- keep the **7-day reset**, but use interpolation only for smoothing, not alerting;
- replace universal `±20%` anomaly logic with **metric-specific, state-specific, persistence-aware** rules;
- keep `<94%` as a conservative **wellness** trigger, not a diagnosis;
- keep the pillar-based GHI, but make penalties bounded and confidence-aware.

## Source references

- Oura Readiness Score: https://support.ouraring.com/hc/en-us/articles/360025589793-Readiness-Score
- Oura Readiness Contributors: https://support.ouraring.com/hc/lv/articles/360057791533-Readiness-Contributors
- Oura Blood Oxygen Sensing (SpO2): https://support.ouraring.com/hc/en-us/articles/7328398760851-Blood-Oxygen-Sensing-SpO2
- Google Health readiness score: https://support.google.com/googlehealth/answer/14236710
- Google Health Sleep Score: https://support.google.com/googlehealth/answer/14236513?hl=en
- Garmin Body Battery: https://www.garmin.com/en-US/garmin-technology/health-science/body-battery/
- Garmin HRV Status: https://www.garmin.com/en-US/garmin-technology/health-science/hrv-status/
- WHOOP Recovery: https://www.whoop.com/us/en/thelocker/how-does-whoop-recovery-work-101/
- WHOOP HRV: https://www.whoop.com/us/en/thelocker/heart-rate-variability-hrv/
- Consumer SpO2 validation literature: peer-reviewed hypoxemia validation papers surfaced in recent searches.
