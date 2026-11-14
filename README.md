# Vehick-Management.io

## Current project version

**MileSage Alpha 1.3.0** — service receipt photo workflow added to mobile HTML preview after the safe restore fix following the Alpha 1.2.0 maintenance features (November 14, 2026). Automated code tests passed; desktop and Android manual testing remain pending. No APK has been built or deployed.

The earlier Alpha 1.1.1 patch records the Tacoma's user-configured tire-rotation and oil-service interval changes. GitHub configuration and documentation have been updated; an Android APK has **not** been built, published, or verified, and mobile/desktop testing of the patch remains pending. The standalone mobile HTML remains a preview, and devices may retain older locally saved data until deliberately synchronized.

## MileSage — configured maintenance intervals

Current user-configured service reminders in [`vehicles.json`](vehicles.json) (updated November 14, 2026):

| Vehicle | Tire rotation interval | Oil-change/service interval |
|---|---:|---:|
| 2026 Toyota Tacoma | 5,000 miles | 10,000 miles |
| 2025 Ford Explorer | 5,000 miles | 5,000 miles |

The Tacoma's tire rotation was changed from 10,000 to 5,000 miles, and its oil-change/service interval from 5,500 to 10,000 miles. These are app settings requested by the vehicle owner, **not a verification of manufacturer recommendations**. The saved odometer and service history are separate from these intervals.

**Phone sync note:** The mobile HTML app keeps local data. A GitHub update does not automatically overwrite phone records. Back up any local phone changes before manually importing GitHub `vehicles.json` from **Data & backup**, since import replaces local records. The update has been verified in GitHub but not yet on the phone.

See [`Alpha 1.1 test log`](testing/alpha-1.1/TEST_LOG.md) for the dated change record and the original reset baseline.

## Beta-release requirement — tester-configurable maintenance intervals

**Planned for beta; not implemented in Alpha 1.1.1.** Each beta tester must be able to set and save their **own tire-rotation interval and oil-change/service interval**, independently **for each vehicle**, from within MileSage. Changing these settings must update the next-due mileage and reminders without requiring GitHub or code changes. Testers should be able to edit these values later; stored values should persist across app restarts and backups/restores. Validate that one tester's or vehicle's settings do not overwrite another's.

The current Tacoma and Explorer intervals in `vehicles.json` are alpha test settings, **not mandatory defaults** for all beta testers. The app should distinguish user preferences from manufacturer guidance; beta testers should consult their vehicle's owner manual or maintenance schedule for appropriate intervals.

## Alpha 1.2.0 — Fluid checks and air filters

**Status:** Source-code alpha update, passing automated checks. GUI/device testing is pending; this does not deploy an APK or silently synchronize phone data.

In **Service History → Fluids & Filters**, each vehicle independently tracks:
- Windshield washer fluid: check every **5,000 miles**.
- Engine coolant reservoir: check every **5,000 miles**.
- Each has a **Reset to Full** button usable **at any mileage**, only after manual visual confirmation. It records the date and odometer and restarts that fluid's countdown without changing the other reminder.
- Interior/cabin air filter: record **replacement date and mileage**.
- Exterior/engine air-intake filter: record **replacement date and mileage**.
- Fluid confirmations and air-filter changes appear in the Service History screen as dated records.

The **Excel export** includes these entries in the **Service History** worksheet and in separate **Fluid Checks** and **Air Filters** worksheets. Dates/mileages are preserved in vehicle JSON data, backups and the phone preview's JSON export for later desktop import. Existing vehicle records without new fields load with empty histories.

**Safety:** The app does not measure actual fluid levels. For coolant, only check the designated reservoir when the engine is cool; never remove a hot pressurized radiator/coolant cap. Use the correct level marks and fluid types described by the vehicle's manual.

**Testing:** Run python -m unittest -v test_fluid_filters.py. GitHub Actions checks Python syntax, regression tests, and mobile JavaScript syntax. GUI and device checks remain necessary before a release.


## Alpha 1.2.1 — data-loss protection for phone restores

The phone's **Data & backup → Review GitHub vehicles.json** no longer imports `vehicles.json` that only contains zero-mile placeholders and no tire PSI/history. GitHub checks are now **read-only** and never automatically replace local mobile data. A manual import previews the incoming record count, blocks dangerous GitHub downgrades, and requires confirmation. Local JSON imports warn about reduced odometer values, cleared PSI, missing vehicles, or lost records.

**Recover from saved GitHub backup** lets the user selectively fill blank readings and empty logs from the older `vehicles_backup.json` without downgrading existing phone readings or changing user-configured service intervals. This older backup is not guaranteed to match current vehicle odometers or the most recent pressure settings. Before overwriting, a local recovery snapshot is stored for undo, but browser storage is not a substitute for a downloaded full backup. Do **not** clear browser data or reinstall the app before exporting.

The HTML preview itself must be updated to see these features; importing JSON only replaces **data**, never the app's code. No Android APK has been rebuilt. Test via `node mobile/test_restore_safety.cjs`.


## Alpha 1.3.0 — Service receipt photo entry (phone HTML preview)

In **Service → Log maintenance**, users can tap **Take receipt photo** (rear camera on supported mobile browsers) or **Choose photo** (existing image), then have MileSage suggest entries for **work performed, service date, odometer, total cost, oil/tire countdown resets and cabin/engine air filter replacement** from OCR text. All suggested values are editable before save. A receipt scan never automatically saves or increases vehicle mileage; saving still validates dates, odometer and cost.

OCR uses Tesseract.js v6.0.1 in the phone browser, downloaded as needed; recognition runs on the device. Internet access is required to load OCR resources the first time, and older/local file browsers may block workers. A failed scan leaves manual entry available. Images and raw OCR text are not stored in public GitHub, vehicle JSON or Excel; the user should retain originals separately. Camera access depends on browser support.

This is currently **phone HTML preview functionality, not a new native Android APK**. The photo buttons do not appear if the phone continues running an older locally saved copy of the app. Importing vehicle data does not update application code.

Node parser tests live at `mobile/test_receipt_parser.cjs`; real phone camera/OCR behavior requires hands-on device verification.
