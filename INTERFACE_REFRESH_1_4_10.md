# MileSage 1.4.10 interface candidate

The desktop now opens to a pictured garage with charcoal navigation and the approved terracotta/warm-white colors. Wide windows show two vehicle cards per row; narrow windows stack them. Manage vehicles opens the existing search, sort and Add/Edit/Remove controls. Select a card for its full overview; selected-vehicle quick actions remain below the garage.

Desktop Expenses reads phone other-expense records, adds/deletes entries and attaches local PDFs. Phone PDF references remain intact. Copy the actual PDF separately and attach the local copy to open it on PC. Car History provides manual reported events and annual review reminders, separate from service logs and the live odometer. Resale snapshots and future phone vehicle fields survive desktop saves; the resale editor remains on the phone.

The phone uses the same approved colors, vehicle photo cards and six bottom destinations, including History. Data & backup stays in the header. Current 1.4.10 native fuel gallery OCR/save, Service scanning, multi-page PDFs, reusable backups, resale and tester feedback are retained. Both canonical HTML entrypoints intentionally remain synchronized despite the older filename of the versioned source.

## Tester installation

This is a test candidate, not a confirmed physical-device release. Android versionCode 151, versionName 1.4.10-interface-test. The package ID remains io.reddirtcode.milesage.alpha1410fueltest and uses the existing CI signing-key cache. An installed copy updates only if the signing certificate matches. Older package IDs remain separate installations. Do not uninstall or clear existing data to work around a signature mismatch.

Before changing an existing installation, export Full mobile backup and save actual PDFs separately. The JSON contains PDF references, not PDF bytes. A new tester can start an empty garage with their own vehicles; this APK does not bundle the developer's vehicle JSON. No tester has been invited or messaged automatically.

## Transfer between PC and phone

Desktop Data & backup > Export for Mobile embeds vehicle photos. Transfer the exported JSON and import it on the phone after saving its current full backup. Phone Export vehicles.json now retains other expenses, mileage log and Car History for desktop use; Full mobile backup retains receipt photos too. Desktop storage still reads the vehicle-list vehicles.json file; it does not open a full-backup wrapper directly. There is no automatic live synchronization or conflict merge. Do not overwrite a newer garage with an older export.

## Validation

Isolated desktop tests cover responsive cards, selection, quick-action visibility, embedded phone photos, mobile-field round trips and expense save rollback. Browser checks exercise 360px/390px phones and 1024px tablet layouts, all destinations, Car History persistence, unchanged odometer and desktop export fields. Existing receipt, native-bridge, parser, backup, photo and VIN regression suites remain required. Actual camera/scanner/OCR behavior still requires phone testing; browser tests simulate native callbacks.
