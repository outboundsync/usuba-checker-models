Source: runs/uplift/results.csv (categories defined in runs/uplift/export.py)

| group | model | first try /49 | after Checker fixes /49 | works right away | fixed by Checker | still buggy | fully broken | spend (fixes) |
|---|---|---|---|---|---|---|---|---|
| Frontier models | GPT-5.6 Sol | 21 | 40 | 21 | 19 | 5 | 4 | $4.06 |
| Frontier models | Claude Opus 5.5 | 17 | 36 | 17 | 19 | 10 | 3 | $7.54 |
| Frontier models | Claude Sonnet 5.5 | 9 | 35 | 9 | 26 | 11 | 3 | $3.17 |
| Frontier models | Muse Wonder * | 12 | 33 | 12 | 21 | 14 | 2 | $6.72 |
| Frontier models | Grok 4.7 | 1 | 27 | 1 | 26 | 17 | 5 | $2.38 |
| Frontier models | Gemini 4 Argon | 7 | 27 | 7 | 20 | 19 | 3 | $3.82 |
| Frontier models | Gemini 3.1 Pro | 2 | 17 | 2 | 15 | 20 | 12 | $6.09 |
| Frontier models | Grok 4.3 | 3 | 8 | 3 | 5 | 28 | 13 | $0.57 |
| Open models | Kimi K3 | 3 | 32 | 3 | 29 | 9 | 8 | $2.40 |
| Open models | DeepSeek V4 Pro | 4 | 10 | 4 | 6 | 12 | 27 | $2.75 |
| Open models | Qwen3.6 27B | 4 | 5 | 4 | 1 | 14 | 30 | $2.62 |
| Open models | Qwen3-Coder | 4 | 4 | 4 | 0 | 15 | 30 | $0.31 |

* Muse Wonder ran without zero data retention (its only provider, Meta, is not ZDR). All other models ran with ZDR.
