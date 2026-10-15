# Data provenance

Publisher: **Walmart recruiting competition**. Original source: [Walmart recruiting competition](https://www.kaggle.com/competitions/walmart-recruiting-store-sales-forecasting/data). Retrieved 2026-10-15. Exact filenames, file sizes, download URLs, and SHA-256 checksums are recorded in [sources.json](../data/sources.json).

The files originate from the Walmart recruiting competition. Original competition terms govern the source data. The mirror advertises Apache-2.0, which does not establish authority to replace those original terms. Raw source files are not redistributed. Reported results are aggregates over weekly store/department sales. Mirror pinned to commit d413ff9482a0f1fd3834daa64df3540961d834f6: https://huggingface.co/datasets/large-traversaal/Walmart-sales .

The MIT license applies to original project code only. It does not relicense third-party data or derived data. Raw files are downloaded locally and excluded from Git.

Run `python -m src.download` from the repository root. It verifies existing files, verifies downloads before replacing them, and rejects upstream changes instead of silently analyzing a different version. Kaggle may redirect downloads to signed storage URLs; this build required no credentials. If anonymous access changes, manually download the source file to `data/raw/` and rerun checksum verification.
