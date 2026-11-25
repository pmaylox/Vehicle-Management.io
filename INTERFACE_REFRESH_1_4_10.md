# MileSage 1.4.10 interface candidate

The desktop now opens to a pictured garage with charcoal navigation and the approved terracotta/warm-white colors. Wide windows show two vehicle cards per row; narrow windows stack them. Manage vehicles opens the existing search, sort and Add/Edit/Remove controls. Select a card for its full overview; selected-vehicle quick actions remain below the garage.

Desktop Expenses reads phone other-expense records, adds/deletes entries and attaches local PDFs. Phone PDF references remain intact. Copy the actual PDF separately and attach the local copy to open it on PC. Car History provides manual reported events and annual review reminders, separate from service logs and the live odometer. Resale snapshots and future phone vehicle fields survive desktop saves; the resale editor remains on the phone.

The phone uses the same approved colors, vehicle photo cards and six bottom destinations, including History. Data & backup stays in the header. Current 1.4.10 native fuel gallery OCR/save, Service scanning, multi-page PDFs, reusable backups, resale and tester feedback are retained. Both canonical HTML entrypoints intentionally remain synchronized despite the older filename of the versioned source.

## Tester installation

This is a test candidate, not a confirmed physical-device release. Android versionCode 151, versionName 1.4.10-interface-test. This installs separately as MileSage Interface Test, package ID io.reddirtcode.milesage.alpha1410interface. It cannot update previous MileSage packages. Keep the original installation and import its Full mobile backup into this candidate. PDFs must be transferred separately.

Before changing an existing installation, export Full mobile backup and save actual PDFs separately. The JSON contains PDF references, not PDF bytes. A new tester can start an empty garage with their own vehicles; this APK does not bundle the developer's vehicle JSON. No tester has been invited or messaged automatically.

## Transfer between PC and phone

Desktop Data & backup > Export for Mobile embeds vehicle photos. Transfer the exported JSON and import it on the phone after saving its current full backup. Phone Export vehicles.json now retains other expenses, mileage log and Car History for desktop use; Full mobile backup retains receipt photos too. Desktop storage still reads the vehicle-list vehicles.json file; it does not open a full-backup wrapper directly. There is no automatic live synchronization or conflict merge. Do not overwrite a newer garage with an older export.

## Validation

Isolated desktop tests cover responsive cards, selection, quick-action visibility, embedded phone photos, mobile-field round trips and expense save rollback. Browser checks exercise 360px/390px phones and 1024px tablet layouts, all destinations, Car History persistence, unchanged odometer and desktop export fields. Existing receipt, native-bridge, parser, backup, photo and VIN regression suites remain required. Actual camera/scanner/OCR behavior still requires phone testing; browser tests simulate native callbacks.

Local validation on November 25: 46 Python tests passed before the additional 800x500 Manage Vehicles check; that added check also passed. Twenty existing mobile Node regression suites passed. Real Chrome checks passed for both standalone entrypoints and the new 360px/390px/1024px interface scenarios. GitHub Actions additionally builds and validates the actual packaged Android HTML.

## Signing continuity

The original phone build never cached its debug key: its Actions log reports a cache-path validation error because the configured path did not exist. The prior signing key cannot be recovered from an APK. The first interface-branch APKs with the old package ID therefore failed the upgrade-certificate comparison and must not be installed over the old app. The attempted original-branch rebuild also correctly blocked publication on a certificate mismatch.

The final candidate uses a new, clearly labeled package. CI now creates ~/.android/debug.keystore explicitly, caches that exact file under milesage-alpha1410-interface-signing-v1, and configures Gradle to use it. The artifact signature is checked against this key before publishing. Continue future interface-test builds on this branch/signing-cache context; changing signing context without migrating the key would again prevent in-place updates. This is a debug test key, not production distribution signing.

## Verified candidate

- Successful build: https://github.com/pmaylox/Vehicle-Management.io/actions/runs/45720465926
- Application source commit: 6795a936de26024dbd034a99da420ebf074a51b8.
- APK SHA-256: f98a9da39fce14cbd946f9caddb1e1370c74ef626c446b9811b89375e3548c71.
- New certificate SHA-256: cedeef1c78e2727ee7a578d0728bce0cb35e6c07ad2d671c01c6bce5b349aa67.
- The final Actions log confirms the key was saved under milesage-alpha1410-interface-signing-v1. APK signature matches the explicitly configured key; downloaded APK checksum and embedded HTML were verified locally. No vehicle JSON is bundled.
- Local installer is outside this repository, under ../interface-builds/MileSage-1.4.10-interface-test/MileSage_Alpha_1_4_10_Interface_Test.apk. Do not use earlier interface-branch artifacts that retained the old package ID.
- This is a debug test key retained in the branch CI cache. Cache retention is not production key management; production signing needs a securely backed-up keystore or managed signing service.
