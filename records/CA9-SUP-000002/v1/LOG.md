<!-- PAGE 1 -->
EXHIBIT C — APPLICATION ACTIVITY EXPORT
Prepared January 9, 2026 by Tomas N. Ewan, systems custodian. Source: retained Harborline case application audit table. Filter: employee account MS-214, dates April 29 through May 26, 2024. Times converted to Pacific daylight time from stored UTC event times. Time field is server event receipt time, not necessarily the time the user began a task. The export preserves the event type and case identifier but excludes customer names and private contact information. Event type NOTE_SAVE denotes a client-submitted save request accepted by the server. Event type STATUS_CHANGE denotes an accepted status request. Event type SESSION_END denotes termination of a session, which may occur automatically. The system does not record every keystroke or all periods of active reading.

<!-- PAGE 2 -->
SELECTED EVENTS — MAY 2
16:46 | HC-240502-61 | CASE_OPEN | MS-214
16:55 | HC-240502-61 | NOTE_SAVE | MS-214
17:08 | HC-240502-61 | NOTE_SAVE | MS-214
17:09 | HC-240502-61 | STATUS_CHANGE | MS-214 | closed
17:17 | session | SESSION_END | MS-214
The May 2 event at 17:08 is a user-associated save request, not an automatic session end. The audit table does not contain the client-side text or the duration of editing. A save request may follow typing, a review of previously entered text or a later submission of text prepared before the recorded end of shift. The export does not determine which possibility occurred on May 2. The status change at 17:09 is a separate event.

<!-- PAGE 3 -->
SELECTED EVENTS — MAY 9
16:38 | HC-240509-22 | CASE_OPEN | MS-214
16:54 | HC-240509-22 | NOTE_SAVE | MS-214
17:06 | HC-240509-22 | NOTE_SAVE | MS-214
17:07 | HC-240509-22 | STATUS_CHANGE | MS-214 | closed
17:21 | session | SESSION_END | MS-214
The retained record shows a save after the recorded end of the shift. There is no event field identifying whether the employee was physically at her workstation throughout the interval. No automated batch save is identified for this case in the export. The custodian cannot use these records to calculate a continuous work interval without other evidence. The session end may follow inactivity.

<!-- PAGE 4 -->
SELECTED EVENTS — MAY 16
16:49 | HC-240516-43 | CASE_OPEN | MS-214
16:58 | HC-240516-43 | NOTE_SAVE | MS-214
17:11 | HC-240516-43 | NOTE_SAVE | MS-214
17:12 | HC-240516-43 | STATUS_CHANGE | MS-214 | closed
17:25 | session | SESSION_END | MS-214
The case was associated with the representative's account. The application stores a server time for each accepted event. It does not record the payroll punch in the same table. The timekeeping export is a separate exhibit. The event sequence may be compared with the punch time, but the resulting elapsed interval is not itself a measurement of active work.

<!-- PAGE 5 -->
SELECTED EVENTS — MAY 23
16:43 | HC-240523-17 | CASE_OPEN | MS-214
16:57 | HC-240523-17 | NOTE_SAVE | MS-214
17:07 | HC-240523-17 | NOTE_SAVE | MS-214
17:08 | HC-240523-17 | STATUS_CHANGE | MS-214 | closed
17:23 | session | SESSION_END | MS-214
The save and status change are logged under the employee account. The export does not establish the number of minutes spent preparing a note. It does establish the recorded time of the request and the case identifier. These four sequences were selected by counsel for comparison with the payroll records. The exhibit does not state that all other application events during the four weeks are absent or that every post-shift event is work.

<!-- PAGE 6 -->
ACCESS AND RETENTION NOTE
The operations dashboard used by team supervisors normally shows current queue status, counts of assigned and closed matters, and case identifiers. Detailed audit history is available through an administrative report requested from the systems group. The payroll manager's ordinary payroll screen does not display the case audit table. A supervisor may open a particular case and review its saved note and status. The export does not include a historical log showing which detailed case records the supervisor actually opened. A request for a report is logged when made through the systems ticket process; the retained ticket history for this production has not established such a request for the four disputed dates. These limitations should be distinguished from a categorical assertion that the employer could never obtain the data.
