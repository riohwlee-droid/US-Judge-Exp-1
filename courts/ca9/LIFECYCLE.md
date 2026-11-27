# CA9 procedural lifecycle v2 (2026-11-27)

Authority: General Orders (Oct 27 2026) §§3.2(h)-(i), 3.3(c)-(e), 5.1, 5.4–5.7; FRAP 26, 34, 36, 40, 41; Circuit Rules 40-2/40-3; 28 USC 46(d). See official links in OPERATIONS.md. This is a conservative executable subset, not an exhaustive legal expert system.

All ca9.* events include case_id, legal_review_completed=true and rule_basis. Documents required by an event must already be registered, filed and in the same case. Events are replayed atomically. No real private information.

| Event | Additional payload and effect |
|---|---|
| case.register | assigned_judges=[], panel_kind=ordinary_merits, origin_district, calendar_location, conflict_review_completed, jurisdiction_basis. Complete initial documents required by storage. |
| ca9.assign | seed, calendar_review_completed, calendar_month, case_weight, priority_review, slots[{id,location,month,judges,conflicts,remaining_weight}]. Filter reviewed slots then deterministic lot. |
| ca9.panel_change | outgoing_judge_id, reason, mode=quorum/same_location_switch/lot; quorum remaining_votes; switch same_location_review/incoming_judge_id; lot seed/switch_unavailable; parties_notified for replacement. |
| ca9.judgment | controlling_opinion_id, judgment_document_id, calendar_verified, federal_party_civil, holidays (ISO dates); optional rehearing_due_override and deadline_order_id. |
| ca9.rehearing_file | petition_document_id, kind=panel/en_banc/both. |
| ca9.response_request / response_file | petition_document_id and order_document_id / response_document_id. |
| ca9.panel_rehearing | petition_document_id, complete votes{judge:bool}, order_document_id; grant requires response or reviewed exception, withdrawal of prior judgment. |
| ca9.en_banc_call | judge_id, ground, call_timing_reviewed; reviewed call_due override if applicable. |
| ca9.en_banc_open | party_opportunity_completed, memoranda_completed, roster_complete, optional vote_due. Restart if electorate changed. |
| ca9.en_banc_vote | judge_id, vote bool. |
| ca9.en_banc_tally | order_document_id; after vote deadline, missing vote counts no (ordinary cases only). |
| ca9.en_banc_draw | seed, clerk_draw_witnessed, optional senior_elections (eligible original panel members). |
| ca9.en_banc_clear | all_notice_call_periods_checked, order_document_id if petitions pending. |
| ca9.stay_file / stay_decide / stay_end | motion_document_id; grant bool, order_document_id, substantial_question, good_cause, until; reason expired/court_order/certiorari_denied, applicable order or no_extension_or_cert_notice. |
| ca9.mandate | mandate_document_id, certified_judgment_and_costs_reviewed, optional timing_order_id. |
| ca9.mandate_recall | order_document_id, extraordinary_circumstances, authority_reviewed. |

Merits: register → assign → hearing → conference → draft → circulation → issue → judgment. After panel change, preserve old panel and drafts, reset new merits round; quorum retains submission and requires agreement. Each opinion snapshots panel and epoch. En banc grant vacates prior issued opinions and downgrades registered precedents immediately; new 11-member panel then hears/decides. GO 5.7 senior member of majority assigns writing; six votes ordinarily needed, rather than two. FRAP 40 filing dates are Pacific dates with reviewed holidays (14 days generally; 45 in qualifying federal-party civil cases). FRAP 41 normally seven days from latest relevant deadline/denial, subject to order or immediate cert denial; review/stay blockers tracked. Mandate closes ordinary appellate docket; not a guarantee of no Supreme Court review. Recall is exceptional.

Limitations: slots, workload/priority review and conflicts supplied by clerk simulation; no court-wide calendar optimization or proof of unbiased seed; linked/comeback/expedited cases and screening/motions panels need separate treatment. No original en banc/full-court rehearing, capital cases, less-than-11 exceptions, senior-status roster-change event, automatic GO 5.4 notice/withdrawal or all internal memo timers, concurrent amendment/call, cert petition extension workflow, detailed stay extensions, or automatic jurisdiction/costs/legal correctness. For these stop and review, do not use ordinary path. Internal deadlines and holiday list require verification, not invented dates. Do not create a live case until profile ready, roster and complete record verified.
