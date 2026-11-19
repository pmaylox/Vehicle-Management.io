# MileSage Alpha 1.4.5 — Second Tester Guide

**Build:** MileSage Tester 1.4.5 (Android debug APK; pre-release)
**Tester group:** trusted closed alpha, tester #2
**Important:** This test installation has its own application storage. It is not a production Google Play release.

## Install and begin
1. Obtain the APK directly from the person who invited you to test MileSage. Do not install copies from unknown senders.
2. Install and open **MileSage Tester 1.4.5** on your Android phone.
3. Start with an empty garage. Add a test vehicle or your own vehicle; do **not** import the developer's personal vehicle backup.
4. Test mileage updates, fuel logging, service logging, expense receipts and PDF scans as available. Confirm all auto-filled information before saving.
5. Open **Graphs → Resale value vs. odometer**. Mileage updates are reflected automatically. The **Open Kelley Blue Book valuation** button opens KBB in your browser. Record a quote manually; no KBB price is fetched automatically.
6. Verify information remains after closing and reopening MileSage.
7. Use **Data & backup → Full mobile backup** to keep your own data. A JSON backup contains document references but **not** scanned PDF bytes; export PDFs separately.

## Send feedback
1. Tap the visible **Feedback / Bug Report** button or **Data & backup → Open tester feedback form**.
2. Choose type and severity, describe what happened and, for bugs, provide reproduction steps.
3. Tap **Save & share feedback**, then select a messaging or email app and your inviter as recipient. You can also **Save feedback on this phone only** and share a stored report later.
4. If the issue is visual, attach a screenshot separately in your message if you wish. Do not send passwords, VINs, receipts, addresses, license plates or other identifying data unless you explicitly choose to.

**Privacy:** Report data is stored locally until you choose to share it. MileSage does not run an automatic issue-submission server. The app cannot confirm whether your message was delivered. The report text does not automatically include vehicle records, photos, odometer readings or device identifiers.

## Suggested initial tests
- Add a new vehicle and switch between vehicles.
- Use + Add, − Subtract, and = Set exact for mileage; verify corrections do not change other vehicles.
- Capture a fuel receipt; verify date, gallons and total.
- Capture a service receipt; verify suggested fields before saving.
- Scan multi-page expense paperwork; view and export the PDF.
- Record two manual resale snapshots on Graphs; verify they remain after reopening the app.
- Export and browse the same JSON backup more than once.
- Submit one bug report and one feature idea using the feedback screen.

## Known alpha limitations
- Expense and receipt OCR is not perfect; always verify fields.
- Kelley Blue Book values are **manual** until authorized data integration is available.
- Scanned PDFs must be exported separately before uninstalling or moving phones.
- Alpha builds can have bugs. Save a Full mobile backup before major tests.
