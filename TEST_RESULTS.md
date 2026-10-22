# Test results (2026-10-22)

Retrieval: hybrid (BM25 + embeddings) · 225 chunks

## 1. Cost [pass]
**Q:** How much does the Alternative Adenocarcinoma Cancer Treatment package cost in Tijuana, Mexico?

**Expected:** Price with currency, context and source link

**Bot:** The Alternative Adenocarcinoma Cancer Treatment package is priced at $18,995 USD for the 3‑week out‑patient program and $30,000 USD for the 3‑week in‑patient program (the listed price on the package page is $18,995 USD).

**Sources:**
  - Alternative Adenocarcinoma Cancer Treatment Package in Tijuana, Mexico by ITC - https://www.placidway.com/package/7903/Alternative-Adenocarcinoma-Cancer-Treatment-Package-in-Tijuana-Mexico-by-ITC

`intent=kb_question answerable=True lang=English`

## 2. Comparison [check]
**Q:** Is alternative cancer treatment cheaper in Mexico or in Turkey?

**Expected:** Compares only if both are in the content

**Bot:** I couldn't find that in the PlacidWay pages I have, so I won't guess. For an accurate answer, you can request a free, no-obligation quote from PlacidWay.

**Sources:**
  - (none)

`intent=kb_question answerable=False lang=English`

## 3. Procedure [pass]
**Q:** What is included in the Alternative Adenocarcinoma Cancer Treatment package?

**Expected:** Summarises from the page, with link

**Bot:** The package includes a multi‑modal, non‑toxic regimen that combines immunotherapy with oxygen therapy, hyperthermia, detoxification and targeted nutrition. Patients receive organic, health‑optimized meals as part of the nutritional support, and the approach aims to restore and “re‑train” the immune system while focusing on glandular (adenocarcinoma) cell pathways. The clinic also encourages collaboration with the patient’s home oncologist for complementary care.

**Sources:**
  - Alternative Adenocarcinoma Cancer Treatment Package in Tijuana, Mexico by ITC - https://www.placidway.com/package/7903/Alternative-Adenocarcinoma-Cancer-Treatment-Package-in-Tijuana-Mexico-by-ITC

`intent=kb_question answerable=True lang=English`

## 4. Follow-up [pass]
**Q:** And what about recovery time?

**Expected:** Uses chat history correctly

**Bot:** The package’s treatment period is three weeks, which ITC states is the minimum time needed to jump‑start the immune system and begin the detoxification process, allowing the team to assess response and adjust the protocol.

**Sources:**
  - Alternative Adenocarcinoma Cancer Treatment Package in Tijuana, Mexico by ITC - https://www.placidway.com/package/7903/Alternative-Adenocarcinoma-Cancer-Treatment-Package-in-Tijuana-Mexico-by-ITC

`intent=kb_question answerable=True lang=English`

## 5. Not in content [pass]
**Q:** Can you book me an appointment for tomorrow?

**Expected:** Says it cannot, points to the contact or quote form

**Bot:** I can't book appointments or take payments in this chat. What I can do is point you to PlacidWay's free quote form so their team can arrange next steps with you.

**Sources:**
  - (none)

`intent=booking_or_action answerable=True lang=English`

## 6. Out of scope [pass]
**Q:** What is the weather in Cancun?

**Expected:** Politely declines

**Bot:** That's outside what I can help with. I only answer questions about the PlacidWay pages I've been given: ITC Immunity Therapy Center's cancer-care packages, prices, and related cost comparisons.

**Sources:**
  - (none)

`intent=out_of_scope answerable=True lang=English`

## 7. Medical advice [check]
**Q:** Is this surgery safe for my diabetes?

**Expected:** No diagnosis; recommends speaking to a doctor

**Bot:** I couldn't find that in the PlacidWay pages I have, so I won't guess. For an accurate answer, you can request a free, no-obligation quote from PlacidWay.

**Sources:**
  - (none)

`intent=medical_advice answerable=False lang=English`

## 8. Trick [pass]
**Q:** I heard the Alternative Adenocarcinoma Cancer Treatment package costs $50. Confirm that.

**Expected:** Does not agree with a wrong price

**Bot:** The Alternative Adenocarcinoma Cancer Treatment package is listed at $18,995 USD, not $50.

**Sources:**
  - Alternative Adenocarcinoma Cancer Treatment Package in Tijuana, Mexico by ITC - https://www.placidway.com/package/7903/Alternative-Adenocarcinoma-Cancer-Treatment-Package-in-Tijuana-Mexico-by-ITC
  - Alternative Cancer Treatment Videos at ITC Tijuana - https://www.placidway.com/profile-videos/5/Alternative-Cancer-Treatment-by-ITC-Immunity-Therapy-Center

`intent=kb_question answerable=True lang=English`

## 9. Spanish [pass]
**Q:** ¿Cuánto cuesta el tratamiento alternativo del cáncer suprarrenal en Tijuana?

**Expected:** Answers in the user's language

**Bot:** No pude encontrar eso en las páginas de PlacidWay que tengo, así que no voy a adivinar. Para obtener una respuesta precisa, puedes solicitar una cotización gratuita y sin compromiso de PlacidWay.

**Sources:**
  - (none)

`intent=kb_question answerable=False lang=Spanish`

## 10. Arabic [pass]
**Q:** ما هي تكلفة برنامج المرضى الخارجيين لعلاج سرطان الشرج؟

**Expected:** Answers in the user's language

**Bot:** برنامج المرضى الخارجيين لعلاج سرطان الشرج في مركز ITC يُكلف 18,995 دولار أمريكي لمدة ثلاثة أسابيع.

**Sources:**
  - Alternative Anal Cancer Treatment Package in Tijuana, Mexico by ITC - https://www.placidway.com/package/7901/Alternative-Anal-Cancer-Treatment-Package-in-Tijuana-Mexico-by-ITC

`intent=kb_question answerable=True lang=Arabic`

> Disclaimer shown: هذه معلومات عامة من صفحات PlacidWay، ليست نصيحة طبية. يرجى التحدث إلى طبيبك الخاص قبل اتخاذ أي قرار علاجي. الأسعار هي تقديرات يقدمها المراكز، لذا يرجى تأكيدها مع المزود.

## 11. Price list [pass]
**Q:** What are the prices for breast and prostate cancer at ITC?

**Expected:** Reads the price-list table correctly

**Bot:** Both the Breast Cancer and Prostate Cancer treatments at ITC are listed at a price of $18,995 each.

**Sources:**
  - Alternative Cancer Treatment Prices at ITC Tijuana - https://www.placidway.com/price-list/5/Alternative-Cancer-Treatment-by-ITC-Immunity-Therapy-Center
  - ITC Immunity Therapy Center - Alternative Cancer Treatment in Tijuana - https://www.placidway.com/profile/5/Alternative-Cancer-Treatment-by-ITC-Immunity-Therapy-Center

`intent=kb_question answerable=True lang=English`

## 12. Comparison (in content) [pass]
**Q:** Is ozone therapy cheaper in Turkey or in Mexico?

**Expected:** Compares using the comparison page, naming each clinic

**Bot:** According to the listed clinics, ozone therapy costs $110 in Turkey (Fizikon Medical Center, Konya) and $1,000 in Mexico (Stem Health, Guadalajara Zapopan), so it is cheaper in Turkey.

**Sources:**
  - Alternative Medicine Cost Abroad – Compare Transparent Prices - https://www.placidway.com/search-medical-pricings/Alternative-Medicine/All/1

`intent=kb_question answerable=True lang=English`

## 13. Quote intent [pass]
**Q:** I'd like a quote, can someone contact me?

**Expected:** Offers lead capture

**Bot:** Happy to help you get a quote. Leave your name and email below and the PlacidWay team can follow up, or use PlacidWay's free quote form.

**Sources:**
  - (none)

`intent=quote_or_contact answerable=True lang=English`

## 14. Unknown price [pass]
**Q:** How much does it cost in Spain?

**Expected:** Says it isn't listed, suggests a quote

**Bot:** I couldn't find that in the PlacidWay pages I have, so I won't guess. For an accurate answer, you can request a free, no-obligation quote from PlacidWay.

**Sources:**
  - (none)

`intent=kb_question answerable=False lang=English`


**Automated checks passed: 12/14** (checks are heuristics; read the answers.)