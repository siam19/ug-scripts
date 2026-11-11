# Evaluation Report: `baseline`

**Date:** 2026-11-11 02:44:18 UTC  
**Products Evaluated:** 12  
**Total Scripts Generated:** 36  

## Summary Scorecard

| Metric | Result | Target Benchmark |
| :--- | :--- | :--- |
| **Overall Hard Rules Pass Rate** | `94.4%` | >= 90% |
| **Structure Pass Rate** (Hook 1st, CTA Last, Valid Reasons) | `91.7%` | >= 95% |
| **Word Count Range Pass Rate** | `100.0%` | >= 85% |
| **Hook Brevity Pass Rate** (<= 12 words) | `8.3%` | >= 90% |
| **Banned Cliché Violations** | `2` hits (5.6%) | 0 hits |
| **Bengali Script Ratio** (Bangla scripts) | `0.985` | >= 0.85 |
| **Average Script Word Count** | `72.6` words | 60 - 90 words |
| **Average Hook Word Count** | `15.0` words | <= 10 words |
| **Average TTFC** (Time to First Content) | `7.51s` | <= 4.5s |
| **Average Total Pipeline Latency** | `18.18s` | <= 8.0s |
| **Average Tokens per Product** | `13705.0` tokens | - |

## Per-Product Breakdown

| Product | Lang | Words (Min/Avg/Max) | Hook Brevity | Banned Hits | Stage 1 (s) | Total (s) | Pass? |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| Radhuni Biryani Masala (40g) | bn | 60/63.0/66 | 15.0 words | 0 | 9.94s | 19.75s | ✅ |
| Ispahani Mirzapore Best Leaf... | bn | 71/77.0/80 | 16.7 words | 0 | 7.65s | 18.43s | ✅ |
| Walton Non-Frost Inverter Re... | bn | 74/76.3/80 | 13.7 words | 0 | 6.96s | 16.79s | ✅ |
| Pepsodent Sensitive Expert P... | bn | 71/73.3/77 | 16.3 words | 0 | 7.31s | 22.4s | ✅ |
| PRAN Mango Fruit Drink (Tetr... | bn | 63/74.0/85 | 14.7 words | 0 | 6.77s | 17.53s | ✅ |
| Taaga Flared Maroon Cotton L... | bn | 69/71.3/75 | 12.0 words | 0 | 6.96s | 21.3s | ✅ |
| Apex Maverick Men's Suede Lo... | bn | 61/69.3/75 | 15.3 words | 0 | 7.37s | 18.12s | ✅ |
| Fresh Fortified Soyabean Oil... | bn | 65/75.3/95 | 16.3 words | 0 | 6.76s | 16.28s | ✅ |
| RFL Knock-Down Multi-Drawer ... | bn | 80/86.3/98 | 15.3 words | 1 | 7.06s | 17.51s | ⚠️ |
| bKash Mobile Financial Servi... | bn | 65/68.3/73 | 14.3 words | 0 | 6.86s | 16.4s | ✅ |
| 10 Minute School Ghore Boshe... | bn | 61/67.0/76 | 16.0 words | 0 | 6.96s | 14.07s | ✅ |
| Shajgoj 100% Authentic Beaut... | bn | 62/69.3/78 | 14.3 words | 1 | 9.48s | 19.6s | ⚠️ |

---
*Report generated automatically by `apps/api/evals/run.py`.*