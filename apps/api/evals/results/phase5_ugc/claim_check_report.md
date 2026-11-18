# Claim Verification Evaluation Report

**Date:** 2026-11-18 12:32:20 UTC  
**Input:** `results.jsonl`  
**Mode:** `mock (offline heuristic)`  
**Products Evaluated:** 11  
**Total Scripts Evaluated:** 33  

## Summary Scorecard

| Metric | Result |
| :--- | :--- |
| **Total Factual Claims Extracted** | `99` |
| **Supported Claims** | `61` (`61.6%`) |
| **Unsupported Claims** (absent / extrapolated) | `38` |
| **Contradicted Claims** (conflicts with facts) | `0` |
| **Total Ungrounded Claim Rate** | `38.4%` (38/99) |
| **Clean Scripts (0 Ungrounded Claims)** | `9/33` (`27.3%`) |

## Per-Product Breakdown

| Product | Lang | Facts | Scripts | Claims | Supported | Unsupported | Contradicted | Ungrounded % | Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| Radhuni Biryani Masala (40g) | bn | 6 | 3 | 6 | 4 | 2 | 0 | 33.3% | ⚠️ |
| Ispahani Mirzapore Best Leaf Tea... | bn | 6 | 3 | 13 | 8 | 5 | 0 | 38.5% | ⚠️ |
| Walton Non-Frost Inverter Refrig... | bn | 7 | 3 | 17 | 13 | 4 | 0 | 23.5% | ⚠️ |
| Pepsodent Sensitive Expert Profe... | bn | 7 | 3 | 9 | 9 | 0 | 0 | 0.0% | ✅ |
| PRAN Mango Fruit Drink (Tetra Pa... | bn | 6 | 3 | 7 | 7 | 0 | 0 | 0.0% | ✅ |
| Taaga Flared Maroon Cotton Long ... | bn | 6 | 3 | 4 | 3 | 1 | 0 | 25.0% | ⚠️ |
| Apex Maverick Men's Suede Loafer... | bn | 7 | 3 | 7 | 2 | 5 | 0 | 71.4% | ⚠️ |
| Fresh Fortified Soyabean Oil (5L... | bn | 7 | 3 | 11 | 8 | 3 | 0 | 27.3% | ⚠️ |
| RFL Knock-Down Multi-Drawer Ward... | bn | 7 | 3 | 10 | 1 | 9 | 0 | 90.0% | ⚠️ |
| bKash Mobile Financial Services ... | bn | 8 | 3 | 5 | 1 | 4 | 0 | 80.0% | ⚠️ |
| 10 Minute School Ghore Boshe Spo... | bn | 7 | 3 | 10 | 5 | 5 | 0 | 50.0% | ⚠️ |

## Flagged Claims (Unsupported or Contradicted)

1. **[UNSUPPORTED]** `Radhuni Biryani Masala (40g)` — *The Eager Newlywed Cook* (Line 2): মশলার পারফেক্ট ব্যালেন্স নষ্ট হওয়ার ভয়ে আছেন  
   - Related Fact IDs: `none` | Rationale: Insufficient overlap with verified product facts.
2. **[UNSUPPORTED]** `Radhuni Biryani Masala (40g)` — *The Time-Strapped Weekend Parent* (Line 3): মাত্র ৪০ গ্রামের এই এক প্যাকেট দিয়েই ৩০ মিনিটে পুরো রান্না শেষ  
   - Related Fact IDs: `none` | Rationale: Numeric claim '30' not found in product facts.
3. **[UNSUPPORTED]** `Ispahani Mirzapore Best Leaf Tea (200g)` — *The Daily 'Adda' Host* (Line 3): সেরা বাগান থেকে বেছে নেওয়া প্রিমিয়াম পাতায় গরম জল ঢালতেই দেখুন কী দারুণ সোনালী-বাদামী লিকার তৈরি হচ্ছে  
   - Related Fact IDs: `none` | Rationale: Insufficient overlap with verified product facts.
4. **[UNSUPPORTED]** `Ispahani Mirzapore Best Leaf Tea (200g)` — *The Daily 'Adda' Host* (Line 4): এই কড়া স্বাদ আর চমৎকার সুবাসে আমাদের ফ্যামিলি আড্ডাগুলো এখন জমে ওঠে একদম অন্য মাত্রায়  
   - Related Fact IDs: `none` | Rationale: Insufficient overlap with verified product facts.
5. **[UNSUPPORTED]** `Ispahani Mirzapore Best Leaf Tea (200g)` — *The Hardworking Office 'Cha-Khor'* (Line 2): একজন আসল চা-খোর হিসেবে আপনার দরকার এক কাপ খাঁটি রিফ্রেশমেন্ট  
   - Related Fact IDs: `none` | Rationale: Insufficient overlap with verified product facts.
6. **[UNSUPPORTED]** `Ispahani Mirzapore Best Leaf Tea (200g)` — *The Household Quality Controller* (Line 1): প্যাকেট খোলার কয়েকদিন পরেই কি চায়ের সুগন্ধ হারিয়ে যায়  
   - Related Fact IDs: `none` | Rationale: Insufficient overlap with verified product facts.
7. **[UNSUPPORTED]** `Ispahani Mirzapore Best Leaf Tea (200g)` — *The Household Quality Controller* (Line 6): দেখুন, প্রতিটি কাপে ঠিক প্যাকেটের ছবির মতোই চমৎকার সোনালী-বাদামী রঙ আর দারুণ লিকার পাবেন  
   - Related Fact IDs: `none` | Rationale: Insufficient overlap with verified product facts.
8. **[UNSUPPORTED]** `Walton Non-Frost Inverter Refrigerator (347L)` — *Budget-Conscious Middle-Class Families* (Line 5): আজই ওয়ালটন শোরুমে গিয়ে আপনার বাজেট-বান্ধব ফ্রিজটি বেছে নিন  
   - Related Fact IDs: `none` | Rationale: Insufficient overlap with verified product facts.
9. **[UNSUPPORTED]** `Walton Non-Frost Inverter Refrigerator (347L)` — *Aesthetic-Focused Urban Homemakers* (Line 1): রান্নাঘরে এখনো সেই পুরনো, দেখতে বাজে মেটাল ফ্রিজটাই রাখছেন  
   - Related Fact IDs: `none` | Rationale: Insufficient overlap with verified product facts.
10. **[UNSUPPORTED]** `Walton Non-Frost Inverter Refrigerator (347L)` — *Load-Shedding Worried Suburbanites* (Line 1): ভোল্টেজ আপ-ডাউন নিয়ে টেনশন  
   - Related Fact IDs: `none` | Rationale: Insufficient overlap with verified product facts.
11. **[UNSUPPORTED]** `Walton Non-Frost Inverter Refrigerator (347L)` — *Load-Shedding Worried Suburbanites* (Line 2): আমাদের এলাকায় ঘন ঘন লোডশেডিং আর ভোল্টেজ ওঠা-নামার কারণে দামি ইলেকট্রনিক্স নষ্ট হওয়া এখন সাধারণ ব্যাপার  
   - Related Fact IDs: `none` | Rationale: Insufficient overlap with verified product facts.
12. **[UNSUPPORTED]** `Taaga Flared Maroon Cotton Long Dress` — *The Comfort-First Young Mother* (Line 4): এই ট্রপিকাল গরমে যেকোনো ফ্যামিলি গ্যাদারিং বা বাচ্চার পেছনে দৌড়াদৌড়ির জন্য এর রিল্যাক্সড ফিট একদম পারফেক্ট  
   - Related Fact IDs: `none` | Rationale: Insufficient overlap with verified product facts.
13. **[UNSUPPORTED]** `Apex Maverick Men's Suede Loafers` — *The Busy Corporate Commuter* (Line 2): সেই ভারী, শক্ত ফর্মাল জুতা বাদ দিন যা পা ঘামায় আর ফোস্কা ফেলে  
   - Related Fact IDs: `none` | Rationale: Insufficient overlap with verified product facts.
14. **[UNSUPPORTED]** `Apex Maverick Men's Suede Loafers` — *The Festive Traditionalist* (Line 1): পাঞ্জাবির সাথে মানানসই ও আরামদায়ক জুতো পাচ্ছেন না  
   - Related Fact IDs: `none` | Rationale: Insufficient overlap with verified product facts.
15. **[UNSUPPORTED]** `Apex Maverick Men's Suede Loafers` — *The Festive Traditionalist* (Line 2): উৎসবে ঘণ্টার পর ঘণ্টা দাঁড়িয়ে থাকলে পায়ে ভীষণ ব্যথা হয়, তাই না  
   - Related Fact IDs: `none` | Rationale: Insufficient overlap with verified product facts.
16. **[UNSUPPORTED]** `Apex Maverick Men's Suede Loafers` — *The Smart-Casual Minimalist* (Line 1): জুতা দিয়ে ওয়ারড্রোব ভরানোর দিন শেষ, এই একটাই যথেষ্ট  
   - Related Fact IDs: `none` | Rationale: Insufficient overlap with verified product facts.
17. **[UNSUPPORTED]** `Apex Maverick Men's Suede Loafers` — *The Smart-Casual Minimalist* (Line 3): এর আনলাইনড মিনিমালিস্ট ডিজাইন গরমে মোজা ছাড়াই খালি পায়ের আরাম দেয়  
   - Related Fact IDs: `none` | Rationale: Insufficient overlap with verified product facts.
18. **[UNSUPPORTED]** `Fresh Fortified Soyabean Oil (5L)` — *Health-Conscious Bangladeshi Homemakers* (Line 5): আর পাঁচ ধাপের ডিওডোরাইজেশন প্রযুক্তিতে পরিশোধিত বলে এটি যেমন হালকা, তেমনি এর রান্নায় কোনো ভারী গন্ধ থাকে না  
   - Related Fact IDs: `none` | Rationale: Insufficient overlap with verified product facts.
19. **[UNSUPPORTED]** `Fresh Fortified Soyabean Oil (5L)` — *Friday Feast & Large Family Hosts* (Line 1): বড় ফ্যামিলির ফ্রাইডে রান্নায় ছোট বোতলের ঝামেলা আর কত  
   - Related Fact IDs: `none` | Rationale: Insufficient overlap with verified product facts.
20. **[UNSUPPORTED]** `Fresh Fortified Soyabean Oil (5L)` — *Active Young Urban Professionals* (Line 5): আজই এই পাঁচ লিটারের জারটি ট্রাই করুন আর তেলতেলে গন্ধকে বলুন বিদায়  
   - Related Fact IDs: `none` | Rationale: Insufficient overlap with verified product facts.
21. **[UNSUPPORTED]** `RFL Knock-Down Multi-Drawer Wardrobe` — *Hygiene-Conscious Mothers* (Line 1): বাচ্চার কাপড়ে ন্যাপথলিনের ক্ষতিকর গন্ধ ছাড়া পোকা তাড়াবেন কীভাবে  
   - Related Fact IDs: `none` | Rationale: Insufficient overlap with verified product facts.
22. **[UNSUPPORTED]** `RFL Knock-Down Multi-Drawer Wardrobe` — *Hygiene-Conscious Mothers* (Line 2): আমাদের এই আরএফএল মাল্টি-ড্রয়ার ওয়ারড্রোবে আছে ইনসেক্ট রিপেল্যান্ট প্রযুক্তি, যা তেলাপোকা ও পিঁপড়ে দূরে রাখে কোনো কেমিক্যালের গন্ধ ছাড়াই  
   - Related Fact IDs: `none` | Rationale: Insufficient overlap with verified product facts.
23. **[UNSUPPORTED]** `RFL Knock-Down Multi-Drawer Wardrobe` — *Hygiene-Conscious Mothers* (Line 4): ৪ ড্রয়ারের এই কমপ্যাক্ট সাইজে বাচ্চার সব নরম জামাকাপড় একদম সুরক্ষিত আর পরিপাটি থাকে  
   - Related Fact IDs: `none` | Rationale: Numeric claim '4' not found in product facts.
24. **[UNSUPPORTED]** `RFL Knock-Down Multi-Drawer Wardrobe` — *Hygiene-Conscious Mothers* (Line 5): আপনার সোনামণির সুরক্ষায় আজই এটি অর্ডার করুন  
   - Related Fact IDs: `none` | Rationale: Insufficient overlap with verified product facts.
25. **[UNSUPPORTED]** `RFL Knock-Down Multi-Drawer Wardrobe` — *Frequent-Shifting Renters* (Line 2): এই ঝামেলার দিন শেষ  
   - Related Fact IDs: `none` | Rationale: Insufficient overlap with verified product facts.
26. **[UNSUPPORTED]** `RFL Knock-Down Multi-Drawer Wardrobe` — *Frequent-Shifting Renters* (Line 3): কোনো হাতুড়ি বা স্ক্রু ছাড়াই মাত্র কয়েক মিনিটে এটা নিজে নিজেই সেট করে ফেলা যায়  
   - Related Fact IDs: `none` | Rationale: Insufficient overlap with verified product facts.
27. **[UNSUPPORTED]** `RFL Knock-Down Multi-Drawer Wardrobe` — *Frequent-Shifting Renters* (Line 4): ভার্জিন পলিপ্রোপিলিন ও এবিএস প্লাস্টিকের তৈরি এই ৪-ড্রয়ারের ওয়ারড্রোবটি কিন্তু ভীষণ মজবুত আর সাইজেও পারফেক্ট  
   - Related Fact IDs: `none` | Rationale: Numeric claim '4' not found in product facts.
28. **[UNSUPPORTED]** `RFL Knock-Down Multi-Drawer Wardrobe` — *Frequent-Shifting Renters* (Line 5): এতে আছে বিশেষ ইনসেক্ট রিপেল্যান্ট প্রযুক্তি, যা জামাকাপড়কে তেলাপোকা আর পিঁপড়া থেকে বাঁচায়  
   - Related Fact IDs: `none` | Rationale: Insufficient overlap with verified product facts.
29. **[UNSUPPORTED]** `RFL Knock-Down Multi-Drawer Wardrobe` — *Aesthetic Traditional Homemakers* (Line 2): দামি কাঠের ফার্নিচার ছাড়াই ঘর সাজাতে চান  
   - Related Fact IDs: `none` | Rationale: Insufficient overlap with verified product facts.
30. **[UNSUPPORTED]** `bKash Mobile Financial Services App` — *Rural Remittance & Utility Homemakers* (Line 1): ঘণ্টার পর ঘণ্টা লাইনে দাঁড়িয়ে বিল দেওয়ার দিন কি শেষ  
   - Related Fact IDs: `none` | Rationale: Insufficient overlap with verified product facts.
31. **[UNSUPPORTED]** `bKash Mobile Financial Services App` — *Cashless Urban Gen Z & Millennials* (Line 2): জাস্ট বিকাশ কিউআর স্ক্যান করে পে করে দিন  
   - Related Fact IDs: `none` | Rationale: Insufficient overlap with verified product facts.
32. **[UNSUPPORTED]** `bKash Mobile Financial Services App` — *Cashless Urban Gen Z & Millennials* (Line 4): তাছাড়া ফিঙ্গারপ্রিন্ট লগইন থাকায় সিকিউরিটি নিয়ে কোনো টেনশনই নাই, আর মোবাইল রিচার্জও করা যায় সেকেন্ডে  
   - Related Fact IDs: `none` | Rationale: Insufficient overlap with verified product facts.
33. **[UNSUPPORTED]** `bKash Mobile Financial Services App` — *Micro-Entrepreneurs & Gig Workers* (Line 3): তাই আমি বিকাশ অ্যাপ থেকে কোনো কাগজপত্র ছাড়াই সাথে সাথে ডিজিটাল ন্যানো-লোন নিয়ে নেই  
   - Related Fact IDs: `none` | Rationale: Insufficient overlap with verified product facts.
34. **[UNSUPPORTED]** `10 Minute School Ghore Boshe Spoken English Course` — *Nervous Job Seekers* (Line 4): কোনো জটিল গ্রামার ছাড়াই আপনি শিখবেন ইন্টারভিউ ও প্রেজেন্টেশনের জন্য ফ্লুয়েন্ট ইংরেজি  
   - Related Fact IDs: `none` | Rationale: Insufficient overlap with verified product facts.
35. **[UNSUPPORTED]** `10 Minute School Ghore Boshe Spoken English Course` — *Stuck Corporate Professionals* (Line 3): জটিল গ্রামার ছাড়াই অফিস প্রেজেন্টেশন আর কনভারসেশনে ফ্লুয়েন্ট হতে আছে মুনজেরিন শাহিদের ঘরে বসে স্পোকেন ইংলিশ কোর্স  
   - Related Fact IDs: `none` | Rationale: Insufficient overlap with verified product facts.
36. **[UNSUPPORTED]** `10 Minute School Ghore Boshe Spoken English Course` — *Busy Academic Students* (Line 1): গ্রামার মুখস্থ না করেই স্পোকেন ইংলিশে প্রো হবেন কীভাবে  
   - Related Fact IDs: `none` | Rationale: Insufficient overlap with verified product facts.
37. **[UNSUPPORTED]** `10 Minute School Ghore Boshe Spoken English Course` — *Busy Academic Students* (Line 2): মুনজেরিন আপুর এই কোর্সে পাচ্ছেন লাইফটাইম অ্যাক্সেস, শিখুন নিজের সুবিধাজনক সময়ে  
   - Related Fact IDs: `none` | Rationale: Insufficient overlap with verified product facts.
38. **[UNSUPPORTED]** `10 Minute School Ghore Boshe Spoken English Course` — *Busy Academic Students* (Line 4): কোনো জটিল গ্রামারের নিয়ম মুখস্থ না করেই সরাসরি প্রেজেন্টেশন আর ইন্টারভিউয়ের জন্য ফ্লুয়েন্টলি কথা বলা শিখুন  
   - Related Fact IDs: `none` | Rationale: Insufficient overlap with verified product facts.

---
*Report generated by `apps/api/evals/claim_check.py`.*