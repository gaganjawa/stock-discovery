# STK-028–030 — Deterministic indicator baseline

Decimal SMA and SMA-seeded EMA; Wilder ATR seeded with the mean of true ranges (first range high-low); relative volume compares current volume with the preceding window; breakout/support exclude the current candle. Warm-up outputs are null. Numerical calculation accepts only finite values; feature boundary rejects mixed instruments, adjustment bases and unordered bars. Dataset quality gate supplies calendar completeness and closed/as-of bars.

Validation: hand references cover SMA/EMA initialization, Wilder smoothing, gap true range, prior-only volume/breakout and zero-volume denominator. Recurring Decimal EMA values checked within 1e-25; prices remain exact Decimal until explicit tick/display rounding. Synthetic reference coverage only. STK-028/029 implemented; STK-030 regression evidence continues with strategy integration. Status: Ready for Release, synthetic scope.
