# Mobile repair audit — November 17, 2026

Reviewed GitHub main `0a9723d`, Android PR #14 head `0b6c898`, the APK attached in the phone chat, current mobile HTML, Android Java/resources/Gradle configuration, workflows, desktop Python syntax and regression suites, and tracked-file inventory. Binary documents and historical exports are reference data, not executable app code. No phone or live desktop records were replaced.

## Confirmed defects and corrections

1. **Installed APK leaks application code onto every screen.** Its `assets/index.html` contains 37,103 characters after the first `</html>` and an unmatched closing script tag. Reproduced raw `${…}` text on Home, Service, Fuel, Expenses and Graphs in a real phone-sized Chrome session. PR #14's newer source removes this tail. Added strict whole-document validation, unique static IDs, leaked-template checks, unit regressions and real browser smoke tests. The build now validates the HTML extracted from the final APK, not only the source script.
2. **New debug APK cannot upgrade the installed test app.** Signing certificate SHA-256 differs between the phone APK (`8ba9265e4576f2109b18fb7c3955e83102b9f4df5dddc1fb46683675621e5091`) and the newer Actions artifact (`9625671576af0e169fc71ba42f72e63dae63ac283a3d8859363a941af27f4b12`). Do not uninstall to resolve this. Repair 1.3.7 uses separate ID `io.reddirtcode.milesage.alpha137repair`, label **MileSage Repair Test**, version code 137. CI caches the repair debug signing key and serializes repair builds to retain the same key for later test upgrades while that cache exists. This is a development signing arrangement, not a production release key; preserve original app and backups.
3. **Import can appear to do nothing.** Added live status for waiting on the picker, reading, validating, confirmation, completion or failure; FileReader fallback and a 20-second read timeout. HTML import, rejected JSON, and record preservation are tested in Chrome. Android provider/camera testing still requires the Samsung device. Do not claim that browser tests prove the native picker works.
4. **Malformed history could be saved and then crash rendering.** `normalize` now rejects null/non-object history entries before commit. Regression imports `[null]` fuel history and verifies storage remains unchanged.
5. **Odometer test failed on Windows checkouts.** Its function-extraction regex assumed LF-only files; now accepts CRLF too. This was a test portability issue, not a broken odometer calculation.

## Known limits and deployment instructions

- HTML/desktop `main` and Android PR #14 are different branches. Do not replace main with the older Android branch: it predates recent desktop photo, VIN and export work. Repair changes are isolated on `codex/mobile-repair-audit`.
- The repair test installs alongside older apps and starts with separate empty storage. Export **Full mobile backup** from the app holding the real records; import that own backup into **MileSage Repair Test**, review replacement warnings, verify both real vehicles and odometers. A desktop export may have stale phone values; never blindly import repository demonstration records.
- Scanned PDF files are not embedded in JSON. Share/back up the PDFs separately and retain the original app.
- Browser localStorage has finite capacity. Photos and up to three recovery snapshots can exhaust it. Failed imports refuse changes rather than erase records. Moving photo storage to IndexedDB is a separate migration, not silently performed during this repair.
- Desktop `photo_path` is a Windows path. Only embedded `mobile_photo` data or a photo chosen on the phone can render on Android.
- Actual Samsung gallery/camera, native scanner, PDF sharing, Android Downloads and native picker return are manual device checks after installation.
