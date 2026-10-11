# STK-031–033 — Swing strategy and sizing

Frozen synthetic baseline: SMA-seeded EMA10 above EMA30, close above prior 20-session high and volume at least 1.5 times prior 20-session average. Entry next session at current high plus fictional .01 tick; stop two Wilder ATR14 below entry, target twice stop distance. Entry window two sessions, maximum holding three sessions, independent forecast endpoint fifth next session. Entry cap 1% above trigger; synthetic adverse stop fill .05 below stop. All prices use directed tick rounding. No confidence percentages.

STK-032 implements STK-003's Decimal linear sizing bounds across cash, planned/combined risk and instrument/sector/gross exposure. Demo uses an explicitly fictional empty portfolio; pending/existing risk must be supplied for concurrent portfolio execution. No real risk profile approved. Gaps can exceed planned stop loss. Synthetic fees: .10/share plus 1 per side; not actual brokerage/tax estimates.

Validation: BUY/WAIT/insufficient branches, earliest next-session entry, exact 2R, future mutation invariance and unchanged capital-risk reference (20 shares; planned loss 106) pass. Paused/stale/no-cash cases block entries. STK-033 UI card is still pending M4. STK-031/032 Ready for Release; synthetic scope only.
