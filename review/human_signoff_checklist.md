# Human Sign-off — Go-Live-Freigabe durch Berufsträger:in

> **Zweck.** Dies ist das **verpflichtende menschliche Prüf- und Freigabe-Gate vor
> jedem Produktivbetrieb** von OPUS PRIME EX. Die deterministische Pipeline, die
> Guardrails und die simulierten internen Reviews (`review/legal_review.md`,
> `review/prompt_review.md`, `review/legal_review_markenrecht_addendum.md`) ersetzen
> **nicht** die Prüfung durch eine zugelassene Berufsträgerin bzw. einen zugelassenen
> Berufsträger. OPUS PRIME EX liefert Rechts-*information*, keine Rechts-*dienstleistung*.
>
> **Wer zeichnet.** Steuerrecht/Finanzen/Gewerbe: **Steuerberater:in** und/oder
> **Rechtsanwält:in**. DSGVO/AI-Act/Data-Act: **Rechtsanwält:in** (IT-/Datenschutzrecht).
> Markenrecht: **Rechtsanwält:in** oder **Patentanwält:in**.
>
> **Ergebnis.** Ohne vollständig abgehakte Pflichtpunkte und unterschriebenes
> Gesamturteil „FREIGEGEBEN" darf das System **nicht** produktiv gegen echte Nutzer
> laufen. Bezug: `spec/OPEN_QUESTIONS.md` #6 (Disclaimer), #9 (Markenrecht),
> #2 (AI-Act-Reviewer); `spec/PROJECT_INSTRUCTIONS.md` O3.

Legende: `[ ]` offen · `[x]` geprüft & bestätigt · `[!]` Änderung erforderlich (unten notieren).

---

## A. Disclaimer-Wortlaut (Pflicht — OPEN_QUESTIONS #6 / O3)

Der folgende Pflichttext wird server-seitig an **jede** materielle Antwort angehängt
(G1, injektionsresistent; Quelle: `src/shared/i18n/de.yaml → pflicht_disclaimer`):

> „Hinweis: Diese Antwort ist eine allgemeine Rechtsinformation auf Basis des
> angegebenen Rechtsstands und ersetzt keine individuelle Beratung durch
> Steuerberater:in oder Rechtsanwält:in. Für verbindliche Auskünfte zu Ihrem
> Einzelfall wenden Sie sich bitte an eine zugelassene Berufsträgerin oder einen
> zugelassenen Berufsträger."

- [ ] Der Wortlaut ist rechtlich ausreichend und final freigegeben.
- [ ] Die englische Fassung (`src/shared/i18n/en.yaml`) ist inhaltsgleich freigegeben.
- [ ] Die KI-Kennzeichnung (Art. 50 KI-VO) in der UI ist ausreichend.

Änderungswunsch (falls `[!]`): ________________________________________________

## B. RDG/StBerG-Scope — vorbehaltene Leistungen (Pflicht)

Der Scope-Filter **G2** blockiert Anfragen nach vorbehaltenen Tätigkeiten und
antwortet mit `ablehnung_vorbehaltene_leistung`. Abgedeckt sind u. a.: Einreichen von
UStVA/Voranmeldung/Steuererklärung, Vertretung vor Finanzamt/Behörde/Gericht,
Markenanmeldung beim DPMA/EUIPO (Muster in `tests/guardrails/test_guardrails.py`).

- [ ] Die Liste der geblockten vorbehaltenen Leistungen ist **vollständig** (keine
      erlaubnispflichtige Tätigkeit rutscht als „Information" durch).
- [ ] Die Abgrenzung Rechts*information* ↔ Rechts*dienstleistung* bei individualisierten
      Zahlen-Subsumtionen in Kurzantworten ist tragfähig (OPEN_QUESTIONS #1).
- [ ] Der Ablehnungstext ist rechtlich sauber (keine faktische Beratung „durch die Hintertür").

Anmerkungen: ________________________________________________

## C. Fachliche Richtigkeit je Domäne (Pflicht)

Stichprobe gegen `evals/golden_set/<domäne>.yaml` (140 Fälle) und die Muss-Normen in
`review/coverage_matrix.yaml`. Pro Domäne mindestens 5 Fälle inhaltlich prüfen.

| Domäne | Golden-Set | Stichprobe geprüft | Normzitate korrekt | Freigabe |
|--------|-----------|:---:|:---:|:---:|
| Steuerrecht | steuerrecht.yaml | [ ] | [ ] | [ ] |
| Gewerberecht | gewerberecht.yaml | [ ] | [ ] | [ ] |
| Finanzen | finanzen.yaml | [ ] | [ ] | [ ] |
| DSGVO | dsgvo.yaml | [ ] | [ ] | [ ] |
| EU AI Act | eu_ai_act.yaml | [ ] | [ ] | [ ] |
| Data Act | data_act.yaml | [ ] | [ ] | [ ] |
| Markenrecht | markenrecht.yaml | [ ] | [ ] | [ ] |

- [ ] Keine erfundenen Fundstellen/Fristen; abweichende Fälle unten dokumentiert.

Gefundene Fehler: ________________________________________________

## D. Markenrecht / Patentanwalts-Vorbehalt (Pflicht — OPEN_QUESTIONS #9)

- [ ] Das simulierte Addendum (`review/legal_review_markenrecht_addendum.md`) ist
      fachlich gegengezeichnet.
- [ ] Die Madrid-Fundstelle §§ 107–118 MarkenG (nicht §§ 119 ff.) ist bestätigt.
- [ ] Die UMV-Artikelnummern (VO (EU) 2017/1001) sind bestätigt.
- [ ] Der Unterschied Widerspruchsfrist DE (ab Eintragung) ↔ EUIPO (ab Anmeldung) stimmt.
- [ ] Patentanwalts-Vorbehalte sind korrekt vom erlaubten Informationsrahmen abgegrenzt.

## E. AI-Act-Selbsteinstufung (Pflicht — OPEN_QUESTIONS #2 / O1)

- [ ] `docs/ai-act-assessment.md` (Negativprüfung aller 8 Anhang-III-Kategorien,
      Art.-50-/Art.-4-/GPAI-Pflichten) ist als fachlich zutreffend bestätigt.
- [ ] Status von ENTWURF auf GEPRÜFT gesetzt (mit Datum/Reviewer).

## F. Zahlen- & Zitat-Provenienz, Rechtsstand (Bestätigung)

- [ ] Prinzip bestätigt: das Modell **berechnet und erfindet nichts** — Zahlen stammen
      aus deterministischen Tools/Quellen (G4), Zitate müssen im Korpus belegt sein (G3).
- [ ] Stale-Warnung (G6) und Drittstaaten-Label (G7) sind sachgerecht.

---

## Gesamturteil

- [ ] **FREIGEGEBEN** — Produktivbetrieb zulässig (im dokumentierten Umfang).
- [ ] **ÄNDERUNGEN ERFORDERLICH** — siehe markierte `[!]`-Punkte; erneute Vorlage nötig.
- [ ] **NICHT FREIGEGEBEN**.

| Feld | Eintrag |
|------|---------|
| Name der/des Berufsträger:in | ____________________________ |
| Zulassung / Kammer / Reg.-Nr. | ____________________________ |
| Geprüfte Domänen | ____________________________ |
| Ort, Datum | ____________________________ |
| Unterschrift | ____________________________ |

**Gültigkeit / Re-Review.** Die Freigabe gilt für den geprüften Rechtsstand und
Funktionsumfang. Eine **erneute Prüfung** ist erforderlich bei: wesentlicher Gesetzes-/
Rechtsprechungsänderung in einer Domäne, Änderung des System-Prompts
(`spec/spec_hashes.json`), Aufnahme einer neuen Domäne/Quelle, oder spätestens nach
**12 Monaten**.

---

*EN summary:* Mandatory human go-live gate. A qualified lawyer / tax advisor (patent
attorney for trademark law) must work through sections A–F and sign the overall verdict
before OPUS PRIME EX serves real users. The deterministic pipeline and simulated internal
reviews do not substitute for this sign-off. This is legal information, not legal advice.
