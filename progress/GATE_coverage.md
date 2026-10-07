# Gate: coverage table (spec 4.3), to be validated before any backtest

Files:
- `results/coverage_cells.csv` and `results/coverage.csv`: spec rule, USD 50k over 7 days;
- `results/coverage_cells_v10k.csv`: robustness at USD 10k;
- `results/figures/coverage_heatmap.png` and `results/figures/theme_indices.png`.

## Result

With the spec rule (at least 60% of weekdays covered in 2024-2025), **only three cells pass**:

| Cell | Coverage (train) | Coverage (test 2026) | Contracts | Volume |
|---|---|---|---|---|
| US / MONETARY | 94% | 100% | 110 | USD 561m |
| GLOBAL / GEOPOLITICS | 77% | 100% | 649 | USD 556m |
| US / FISCAL_POLITICAL | 69% | 100% | 265 | USD 1,187m |

The following cells fail:
- US INFLATION (25%) and US TRADE (31%); at USD 10k they rise to 53%, still below the threshold;
- every non-US G10 cell, below 10% over the training period. JP MONETARY appears only in 2026, with the Kalshi `KXCBDECISION*` series. UK and EA FISCAL are episodic.

**Consequence for Strategy A**: country-relative signals (spec 5) are not feasible on the G10. With only US cells, the relative signal becomes a dollar signal, identical for every pair.

## Consistency check of the indices (bug hunting, no parameter tuning)

- **US MONETARY**, which reacts on the right dates:
  - −4.1 on 2 August 2024 (weak payrolls);
  - +3.9 on 19 December 2024 ("hawkish cut");
  - −4.9 on 1 August 2025 (payroll revisions);
  - a round trip on 20 and 21 November 2025.
- **US FISCAL**: +4.8 on 6 November 2024 (election).
- **GEOPOLITICS**:
  - confirmed shocks on 12, 13 and 17 June 2025 (Israel-Iran);
  - −3.5 on 4 October 2025 (Gaza deal).
- **Shocks**: 19 confirmed over the sample, out of 24 raw.
- **Drift**: the US MONETARY index rises steadily, because "cut by date" markets decay. Trading signals will be demeaned causally (D12).

## Decisions requested

1. **Form of Strategy A** given the coverage.
2. **US fiscal regime** for the sign of the FISCAL theme. Either expansion → USD up (monetary dominance), or expansion → USD down (fiscal dominance).

See `data/manual/fiscal_regime.csv` (draft).

(Both were decided by the team: D14 and D15 in `DECISIONS.md`.)
