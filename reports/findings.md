# Findings

Analyzed 421,570 store-department-week observations from 45 stores, 2010-02-05 through 2012-10-26.

- Highest observed sales: store 20, $301,397,792.46 across 143 weeks.
- Highest department sales: anonymous department 92, $483,943,341.87.
- Retained 1,285 negative sales observations; their cause is not specified, so they are not silently dropped.
- Rolling one-week-ahead final-12-week backtest: naive WMAE $1,119,622.11; seasonal WMAE $1,122,689.16. These are national totals, not department-level competition scores.

Use sales per square foot alongside total sales to compare differently sized stores. Review holiday peaks before staffing and replenishment planning. Department revenue ranks do not measure profitability or individual SKU demand. Holiday comparisons are descriptive and are not causal uplift estimates.

This source has no customer identities, transaction timestamps, cities, item names, unit quantities, costs, channel flags, or inventory. It cannot support peak operating hours, customer segmentation, profit margins, or claims of supply-chain improvement. Rows are weekly aggregates, not transactions.
