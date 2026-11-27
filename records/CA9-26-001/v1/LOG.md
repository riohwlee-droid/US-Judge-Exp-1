<!-- PAGE 1 -->
ASTER QUAY LOGISTICS — DISPATCH RELEASE DATA EXPORT
Custodian: Mina C. Velden. Export scope: Oakland facility, records retained for the common March 21–April 3, 2024 review and the separate Maren February 4–April 3 extended review. Prepared for discovery and reproduced in the May 4, 2026 filing. Times are local; dates before March 10 use PST and dates thereafter use PDT. A release row identifies an account and recorded release event, not the identity of a person who may have spoken to that account holder. The approval field history is stored independently. A blank at release does not by itself establish an unauthorized dispatch. The report below includes the exception rows selected by the audit queries, not all successful releases. No reliable denominator of total eligible transactions is included in this exhibit. The query definition, selected rows, later field changes, and manual note entries are distinct records.

<!-- PAGE 2 -->
QUERY LOG — COMMON WINDOW
Run ID Q-0405, executed April 5, 2024, 14:48 PDT by analyst account DFENMORE. Facility OAK. Date range March 21 00:00 through April 3 23:59. Accounts: EMAREN, JBELLFORD, and four other coordinators identified as Q3, Q4, Q5, Q6 for privacy in this fictional record. Filter: release status sent, approval value absent at release, excluding system test transactions. Output: 12 preliminary rows. Counts: EMAREN 3, JBELLFORD 4, Q3 2, Q4 1, Q5 1, Q6 1. The output was exported to AQ-review-0405 at 15:02. The query did not filter by the later resolution of a flagged transaction, by customer impact, or by whether an oral approval was subsequently confirmed. The query is not a report of total releases. No disciplinary threshold is contained in this query.

<!-- PAGE 3 -->
QUERY LOG — EXTENDED WINDOW
Run ID Q-0415, executed April 15, 2024, 15:39 PDT by DFENMORE. Facility OAK. Date range February 4 00:00 through April 3 23:59. Account: EMAREN only. Same release and absent-at-release filters as Q-0405. Output: 12 preliminary rows. Nine are outside the common window, three inside it. The workbook AQ-Maren-0415 is separately retained. Q-0423 reconciliation uses the same selected rows and does not add new transactions. It adds the analyst's resolution field and references to event-history or manual notes. No extended query for JBELLFORD or Q3–Q6 was located in the retained audit folder. This statement concerns the retained quality query logs, not whether someone could have examined individual records by other means.

<!-- PAGE 4 -->
MAREN — EXCEPTION ROWS 1–4
AQ-3901 | Feb 6 08:52 PST | approval at release blank | manual reference M-206-04 | resolved Apr 23: timely manual approval; delayed field synchronization.
AQ-3956 | Feb 12 14:13 PST | blank | M-212-08 | resolved: lead approval recorded in manual log before release.
AQ-4027 | Feb 19 16:45 PST | blank | M-219-11 | resolved: approval-field event at 16:38; report joins omitted event until refresh.
AQ-4099 | Feb 28 11:27 PST | blank | M-228-03 | resolved: manual log and lead confirmation.
The listed times are the release timestamps. Manual entry time and later electronic refresh are different fields. These four rows appear in the expanded export only. The reconciliation codes do not establish that the employee had knowledge of the export defect at the time of each release.

<!-- PAGE 5 -->
MAREN — EXCEPTION ROWS 5–8
AQ-4182 | Mar 7 15:42 PST | blank | no complete timely reference | open: disputed authorization.
AQ-4210 | Mar 11 09:14 PDT | blank | M-311-01 | resolved: earlier approval event.
AQ-4255 | Mar 14 13:05 PDT | blank | M-314-05 | resolved: timely manual note.
AQ-4311 | Mar 20 16:28 PDT | blank | incomplete reference M-320-09 | open: disputed authorization.
The screen contains no completed approval field for AQ-4182 or AQ-4311 in the release state. The field history does not contain a timely complete manual approval for either. The log does not contain audio or a transcript of any conversation at the dispatch desk. The analyst marked these two entries disputed rather than confirmed unauthorized. The status code describes the available documentation and employee explanation.

<!-- PAGE 6 -->
MAREN — EXCEPTION ROWS 9–12
AQ-4338 | Mar 20 17:04 PDT | blank | M-320-12 | open: manual note lacks lead identity, no separate authorization dispute recorded.
AQ-4402 | Mar 26 10:23 PDT | blank | M-326-03 | resolved: timely approval entry recovered in field history.
AQ-4451 | Mar 29 15:17 PDT | blank | M-329-10 | open: reason field missing; lead identity entered.
AQ-4498 | Apr 3 11:53 PDT | blank | M-403-06 | resolved: timely manual approval.
The latter three entries were present in the common review. After reconciliation, the twelve preliminary rows consist of eight resolved and four open entries. Two open entries are coded disputed authorization and two incomplete documentation. The categorization is an analyst's record assessment, not a final HR finding. No numerical severity score was calculated.

<!-- PAGE 7 -->
BELLFORD — COMMON EXCEPTION ROWS
AQ-4365 | Mar 22 08:31 PDT | blank | M-322-02 | resolved: approval event present before release.
AQ-4418 | Mar 27 13:48 PDT | blank | M-327-04 | open: manual reason field absent.
AQ-4470 | Apr 2 09:56 PDT | blank | M-402-07 | open: destination confirmation incomplete in release screen; later lead confirmation reported by manager.
AQ-4486 | Apr 3 09:02 PDT | blank | M-403-02 | resolved: delayed update.
The common query does not establish whether Bellford had other exceptions between February 4 and March 20. The record of lead confirmation for AQ-4470 is a management notation after the event rather than a contemporaneous recording of a conversation. Quality retained the original blank field in the export and did not backfill the value to represent a later explanation as an earlier approval.

<!-- PAGE 8 -->
OTHER COORDINATORS — COMMON EXCEPTION ROWS
Q3: AQ-4371 Mar 22 10:16, resolved manual note; AQ-4444 Mar 29 08:05, open incomplete reason field.
Q4: AQ-4409 Mar 26 14:39, resolved approval history.
Q5: AQ-4464 Apr 1 16:21, resolved manual note.
Q6: AQ-4491 Apr 3 10:47, resolved approval history.
All times PDT. No employee demographic information is associated with these account labels in the export. The common query returned five flags for the other four accounts, of which four were resolved and one remained open. The file is not a comprehensive personnel discipline database. The fact that an entry remained open does not identify the final corrective action. The export includes the open entry for Q3 to prevent treating Maren and Bellford as the only accounts with incomplete documentation.

<!-- PAGE 9 -->
FIELD HISTORY — AQ-4182
March 7, 15:38:11 PST — destination check complete, account EMAREN.
15:39:02 — carrier identity check complete.
15:42:17 — release message transmitted, approval field null.
15:43:29 — departure scan not yet recorded.
15:51:44 — departure scan entered at loading door.
17:00:00 — shift closed; manual approval reference null in retained structured log.
The export includes the status events available from the transaction and manual-reference tables. A scan after release is not approval. A missing structured note may indicate that a note was not made or that a note kept elsewhere was not retained. There is no recorded error code identifying a failed save for this particular reference. The custodian cannot reconstruct a conversation or a paper note that is not in the retained records.

<!-- PAGE 10 -->
FIELD HISTORY — AQ-4311
March 20, 16:21:03 PDT — identity check complete, account EMAREN.
16:24:10 — destination check complete.
16:28:02 — release message transmitted, approval field null.
16:35:50 — departure scan at loading door.
16:57:12 — manual reference M-320-09 created; reason field: carrier waiting; lead field blank.
17:00:00 — shift closed.
A retained manual entry exists, but the entry does not identify the approving lead. A subsequent note was not inserted into the original record. The entry therefore does not meet the complete-note requirement under the January policy even if the employee obtained oral approval. The field history does not establish that the lead field was blank because of intentional omission. No recording of the claimed oral approval is contained in this system.

<!-- PAGE 11 -->
FIELD HISTORY — AQ-4470
April 2, 09:50:21 PDT — carrier identity complete, account JBELLFORD.
09:55:08 — destination field pending.
09:56:41 — release message transmitted, approval field null.
10:01:26 — destination field completed.
10:06:02 — departure scan recorded.
10:24:00 — manual reference M-402-07; reason field blank; lead name entered.
11:15:00 — customer service ticket created concerning destination confirmation.
April 3, 08:40 — operations note: lead reported telephone confirmation of destination before release. This is not a system event contemporaneous with release. The data show the field was pending at release and later completed; they do not establish whether the substantive destination check was completed by another method at the earlier time. The ticket and note are separate from the original field history.

<!-- PAGE 12 -->
CUSTODIAN CERTIFICATION
The foregoing pages reproduce the retained audit query descriptions, selected exception rows and relevant field-history excerpts. The original electronic tables contain additional technical fields not material to the displayed exception statuses. The parties received machine-readable exports in discovery. I have not made a finding about the truth of a witness's account of oral instructions. The exception reports were generated by a missing-field screen and were later reconciled using the records described in the analyst's report. No extended comparator report is included in the produced quality folder. I certify that the displayed records identify the same accounts, times, status codes and shipment identifiers as the fictional records maintained by the company. These are not actual business records of a real entity.
/s/ Mina C. Velden, May 4, 2026 (fictional).
