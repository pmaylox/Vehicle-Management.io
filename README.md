# MileSage

## Current interface test build

MileSage **Alpha 1.4.10 Interface Test** provides the pictured desktop garage, matching phone colors/navigation, separate Car History, desktop Expenses and the current Android receipt/PDF workflows. The Android test app installs separately as **MileSage Interface Test**. Keep earlier installations and back up their data before transfer. PC and phone data do not automatically synchronize.

- [Phone and desktop user guide PDF](docs/MileSage_1_4_10_Phone_and_Desktop_User_Guide.pdf) - detailed installation, daily workflows, backups, transfer and troubleshooting.
- [Phone and desktop guide HTML](docs/MileSage_1_4_10_Phone_and_Desktop_User_Guide.html) - the same guide in a scrolling format.
- [Verified Android build](https://github.com/pmaylox/Vehicle-Management.io/actions/runs/45720465926) - source 6795a93, with saved interface-test signing key.
- [Interface build notes](INTERFACE_REFRESH_1_4_10.md) - validation and current limitations.
- [Roadmap](ROADMAP.md) - planned tutorial for future Android and desktop builds.

New testers should add their own vehicles or import their own backup. Development GitHub vehicle/recovery files are not a personal cloud account for each tester. Full mobile JSON backup does not contain actual PDF files; export PDFs separately.

The sections below are historical implementation notes. Earlier statements that no APK exists describe those older versions, not the current test build.

## Historical alpha version notes

**MileSage Alpha 1.3.2** — mobile HTML preview adds VIN lookup through NHTSA vPIC with an explicit review-before-save screen. Prior vehicle overview, fuel analytics, receipt-photo features and safe restores remain. Desktop and Android manual testing remain pending. No APK has been built or deployed.

The earlier Alpha 1.1.1 patch records the Tacoma's user-configured tire-rotation and oil-service interval changes. GitHub configuration and documentation have been updated; an Android APK has **not** been built, published, or verified, and mobile/desktop testing of the patch remains pending. The standalone mobile HTML remains a preview, and devices may retain older locally saved data until deliberately synchronized.


## Add a vehicle using its VIN (Alpha 1.3.2)

The mobile garage now includes **+ By VIN** beside **+ Manual**. Enter the 17-character VIN, select **Look up VIN** while online, and review the NHTSA-decoded model year, make and model. Edit the suggested name or year if needed, enter the actual odometer reading and confirm **Save new vehicle**. VIN input excludes the letters I, O and Q, checks NHTSA decoder errors, and rejects a duplicate VIN. **No vehicle is written until final confirmation**. The VIN is stored in the record, displayed on its vehicle card and exported in both JSON backup formats.

This uses the public [NHTSA vPIC VIN Decoder](https://vpic.nhtsa.dot.gov/api/) (an external service) and therefore sends the entered VIN to NHTSA. It is not an ownership check or a vehicle-history report. On a mobile browser that blocks remote network requests from a local HTML file, or when offline, the VIN lookup reports an error and does not change the garage. The **+ Manual** button still works without the decoder.

The desktop Python model now preserves the optional \`vin\` field on save/load, so the mobile export does not silently lose it. Older JSON files without a VIN still load normally. Existing vehicles, including named test vehicles, are not automatically merged, removed or renamed. This update does not insert the user's phone data into GitHub's sample \`vehicles.json\`.

**Upgrading phones safely:** In the currently installed version, export **Full mobile backup**. Download and open the new \`mobile/MileSage_Alpha_1_3_2_VIN_Lookup.html\` file; local browser files can have different storage origins and thus appear blank. Use **Data & backup → Import JSON file** to review/import the user's own saved backup if needed. Do **not** clear the old browser storage or import repository demo data over live records. Inspect all vehicle cards, tester labels, odometers and histories before logging new work. There is no automatic phone app replacement or APK deployment.

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


## Vehicle photos on mobile

Home now displays a photo on each vehicle card. Select a vehicle, then use **Choose vehicle photo** or **Take vehicle photo** below the cards; **Remove photo** leaves its histories intact. Camera capture depends on the phone/browser. Both current distributed HTML copies include this feature.

Images are resized to fit within 900 pixels and stored as PNG data in `mobile_photo`, retaining transparency. Photos remain on the device and are included in **Full mobile backup**. Failed storage writes leave existing records unchanged. Desktop `photo_path` values are preserved but cannot open Windows files on a phone; choose the image on the phone instead. Export your current phone backup before opening the updated HTML, and import that backup if the new copy has separate browser storage. Opening the older installed HTML will not show these controls. No APK update is provided.

Validation: `node mobile/test_vehicle_photos.cjs` checks image preparation, card rendering, backup persistence, failed-save rollback, vehicle isolation and removal. Actual camera/device testing remains manual.

## Alpha 1.3.0 — Service receipt photo entry (phone HTML preview)

In **Service → Log maintenance**, users can tap **Take receipt photo** (rear camera on supported mobile browsers) or **Choose photo** (existing image), then have MileSage suggest entries for **work performed, service date, odometer, total cost, oil/tire countdown resets and cabin/engine air filter replacement** from OCR text. All suggested values are editable before save. A receipt scan never automatically saves or increases vehicle mileage; saving still validates dates, odometer and cost.

OCR uses Tesseract.js v6.0.1 in the phone browser, downloaded as needed; recognition runs on the device. Internet access is required to load OCR resources the first time, and older/local file browsers may block workers. A failed scan leaves manual entry available. Images and raw OCR text are not stored in public GitHub, vehicle JSON or Excel; the user should retain originals separately. Camera access depends on browser support.

This is currently **phone HTML preview functionality, not a new native Android APK**. The photo buttons do not appear if the phone continues running an older locally saved copy of the app. Importing vehicle data does not update application code.

Node parser tests live at `mobile/test_receipt_parser.cjs`; real phone camera/OCR behavior requires hands-on device verification.


### Fuel receipt photo entry (Alpha 1.3.0)

In **Fuel → Record a fill-up**, users can take a pump receipt photo or choose a photo already on the phone. On-device OCR suggests **purchase date, US gallons purchased, total paid, and odometer if printed**. Missing values remain for manual entry. **Full Tank is never inferred** from the receipt; after scanning, it defaults to unchecked and must be explicitly selected if the user actually filled the tank. Odometer readings below the current vehicle mileage are not inserted; higher values remain subject to normal save-time checks. The user must review everything before saving.

The shared OCR engine is downloaded when needed, and image/text are not uploaded to GitHub or stored in vehicle JSON. The Fuel History JSON and Excel export continue to store the confirmed structured transaction details rather than the receipt image. Parsing tests: `node mobile/test_fuel_receipt_parser.cjs`. Live Android camera/OCR tests are still needed.

**Important:** GitHub data restoration only imports data; it does not update the installed HTML or Android app. To see both photo buttons on the phone, the user must open the updated application HTML in a compatible browser or install a newly packaged app (no APK is provided by this update).


## Alpha 1.3.1 — mobile parity for November 14 evening work

The mobile HTML preview now includes **battery, tire PSI, service and fuel overview cards**, plus **miles between recorded fill-ups, per-gallon price and full-tank interval fuel cost per mile** charts. Fuel entries can save optional **fuel type/blend and octane rating** using the same JSON fields as the desktop application. Prior photo OCR and fluid/filter actions remain. Data visualization is based on actual local records and does not invent live readings.

**Device status:** This source update is **not an installed Android update or APK**. The phone continues to use whichever HTML/app package was previously opened; importing `vehicles.json` changes data only, never the app's code. Before opening a new copy of the HTML, export a **Full mobile backup** from the old app; a different browser/file origin may have separate local storage. Import into the new copy only after reviewing the current mileage, tire PSI and history. Do not clear the original browser storage or uninstall anything until the new copy is verified.

**Live-data caution:** `vehicles.json` is currently a mixed development dataset (including an Explorer demonstration vehicle) and is **not** a reliable source of the phone's latest personal readings. Use the phone's own exported backup instead of blindly replacing data with GitHub's current JSON. The older README description of the repository JSON as a fully blank template is historical and not a guarantee of current contents.

**Validation:** `node mobile/test_evening_insights.cjs` tests chart calculations and verifies that original phone storage keys and restore guards remain present. GitHub Actions also checks mobile JavaScript syntax and existing OCR/restore regressions. Manual Android camera, chart and local backup checks still required.
