# MileSage — Alpha 1.1 Testing Log

**Start date:** 2026-11-13 (America/Chicago)
**Test cycle:** Alpha 1.1 — Fresh-Start Data Testing
**Status:** Reset committed in GitHub; device-level testing has not yet been run or verified.
**Repository:** `pmaylox/Vehicle-Management.io`

## Purpose
Test MileSage from a clean data state, keeping the original two vehicle profiles and maintaining existing service-interval settings. The user is testing the app as it is built and asked to reset test records.

## Reset authorized by user
- Retain **2026 Toyota Tacoma** and **2025 Ford Explorer**, including their names, model years and configured oil/tire-rotation intervals.
- Set tracked mileage and starting mileage to **0 miles** on both vehicles. (Tacoma was separately requested at 0 first; the later instruction resets everything.)
- Set last tracked oil-service mileage to 0 for each vehicle; clear last tire-rotation mileages.
- Empty service history, fuel history, and tire-pressure event history.
- Set current and starting tire-pressure readings to `null` (unknown, not 0 PSI).
- Expense and graph totals derived from history start at zero/empty. Mobile-only expenses and mobile mileage logs must also be cleared on the **phone's own copy** by importing the reset data.

## Confirmed initial vehicle state
| Vehicle | Odometer | Oil interval | Tire-rotation interval | Service records | Fuel records | Tire PSI readings |
|---|---:|---:|---:|---:|---:|---|
| 2026 Toyota Tacoma | 0 mi | 5,500 mi | 10,000 mi | 0 | 0 | Not entered |
| 2025 Ford Explorer | 0 mi | 5,000 mi | 5,000 mi | 0 | 0 | Not entered |

## GitHub changes
- Preserved pre-reset JSON snapshot at `testing/alpha-1.1/pre-reset-vehicles-2026-11-13.json` before changing the live data.
- Archive commit: `b50dfdc2a1bdd8afc88f48135b45a9fd99529a66`.
- Reset `vehicles.json` on `main`.
- Reset commit: `6f938261e9e4d1a3e82aff95bb68cf2c507a5601`.
- No application code, mobile HTML, or APK was changed in this reset.

## Alpha 1.1 manual test checklist
All items below are **pending** until tested on the user's device or laptop. Do not label them passed until verified.

- [ ] Import clean `vehicles.json` into phone's MileSage mobile web view via **Data & backup → Import from GitHub**; approve replacement.
- [ ] Confirm **exactly two vehicles** and both display **0 miles**.
- [ ] Confirm both vehicles show **zero service records** and **zero fuel fill-ups**.
- [ ] Confirm previous test spending is gone and expense graphs start empty/zero.
- [ ] Confirm tire pressures display as **not entered**, not as real-time sensor readings or 0 PSI.
- [ ] Record a mileage change and verify it persists after refresh/relaunch.
- [ ] Enter an oil service and verify history, mileage countdown, and totals.
- [ ] Enter a fuel fill-up and verify price, gallons, MPG rules, and totals.
- [ ] Add/update four tire-pressure values and verify pressure history.
- [ ] Check vehicle switch between Tacoma and Explorer without leaking records.
- [ ] Export a backup and reimport it to confirm persistence.
- [ ] Confirm desktop app behaves correctly using newly reset data after a safe Git pull, avoiding overwriting newer unsynced laptop edits.
- [ ] Verify mobile/desktop synchronization boundaries; phone browser edits do not upload to GitHub.
- [ ] Create and install an actual Android APK before testing any app icon or standalone app behavior. The existing mobile HTML is not an APK.

## Known limitations / test notes
The mobile HTML version uses browser `localStorage`. GitHub data is read-only from the phone, and automatic refresh deliberately avoids overwriting phone-only changes. Consequently the GitHub reset **does not guarantee an immediate reset of a phone's existing stored data**. Use **Full mobile backup** first if the local phone data is worth keeping, then **Import from GitHub**, confirm replacement, and verify the dashboard. The standalone Android APK is not yet verified or installed.

The reset changes the application's **tracked test odometers**, not the physical odometers in either vehicle. Tire inflation recommendations must come from the vehicle's placard, not test data.

## Findings & issues
| Date | Test area | Observation | Status |
|---|---|---|---|
| 2026-11-13 | Clean start | Baseline `vehicles.json` reset on GitHub, with archival snapshot | Saved and verified by re-reading GitHub JSON (2 vehicles, 0 miles, 0 service/fuel/pressure records) |
| 2026-11-13 | Mobile synchronization | Existing browser data may need manual confirmed import | Open |
| 2026-11-13 | Android installation | APK not yet verified as installed; previous link showed source code | Open |

## Future entries
For each test: record local date/time, device/build, steps, expected result, actual result, pass/fail, issue ID, fix commit, and retest result.

## 2026-11-13 — Phone retained old records after GitHub reset
- **Observed:** Android browser screenshot at approximately 08:10 local time shows Tacoma **6,881 mi** and Explorer **13,145 mi**; Tacoma showed **7 service records** and **4 fuel fill-ups**.
- **Expected:** Both vehicles display **0 mi** with empty service, fuel, and tire-pressure histories, and zero recorded spending.
- **Repository verification:** The GitHub `main/vehicles.json` file was fetched again and confirmed to have zero mileage and empty histories for both vehicles.
- **Likely cause:** The browser opened the mobile HTML from a `content://media/...` local address, and retained `localStorage` data. Auto-refresh intentionally does not overwrite local changes. The user may have used a backup/export action rather than confirming manual import; exact click sequence not verified.
- **Workaround:** In the mobile HTML, use `Data & backup → Import from GitHub` and **confirm replacement**. If network import fails, download the reset JSON and use `Choose JSON file` within the app. Do not merely open the JSON in a browser. Preserve a full mobile backup first if previous local tests need archiving.
- **Status:** Open — awaiting user verification that phone shows 0 miles and 0 records; not yet marked passed.
- **Follow-up product improvement:** Clearly distinguish Import versus Export/Backup; add a dedicated `Reset test data` control for alpha testing with confirmation, and clearer indication of the browser's local data/sync state.


## 2026-11-13 — Alpha 1.1 Android local HTML link broke
- **Observed:** At approximately 08:20 local time, opening the previously used local MileSage browser tab shows Chrome `ERR_FILE_NOT_FOUND` for `content://media/external/file/1928`.
- **Expected:** MileSage dashboard should open and display retained vehicle data.
- **Assessment:** Android's `content://` URI is a reference to a local document; it is not a stable hosted app URL. The underlying file or Chrome's access to it appears to have disappeared. This does **not** demonstrate that the app repository or reset data was deleted.
- **Workaround:** Reopen the actual MileSage HTML file from Samsung **My Files → Downloads**, or download a fresh `mobile/MileSage_Mobile_Auto_Refresh.html` from GitHub and open the saved HTML file with Chrome. Do not keep using the broken tab or its old `content://` address.
- **Follow-on validation:** Once MileSage launches, use **Data & backup → Import from GitHub** and confirm replacement to restore Alpha 1.1's two zero-mile vehicle profiles. Verify 0 service/fuel records; keep the test marked open until confirmed on device.
- **Product action:** Prioritize a durable HTTPS-hosted mobile preview or actual packaged APK; local content URIs are not suitable as permanent launch shortcuts. Avoid clearing browser storage before exporting anything worth saving.
- **Status:** Open — device-level retest required.

## 2026-11-13 — Downloaded mobile HTML not located in visible Downloads list
- **Observed:** Samsung My Files screenshot at approximately 09:35 local time shows Downloads with seven items, including `READ_ME_FIRST.txt` describing MileSage Mobile installation notes, but no visibly listed `MileSage_Mobile_Auto_Refresh.html`. An overlay at the bottom shows the name `MileSage_Mobile_Auto_Refresh` without confirming a stored HTML file.
- **Likely issue:** The browser's prior `content://` file address is inaccessible, and the required mobile HTML might be absent, stored elsewhere, or not visible in the current list. Not yet proven deleted.
- **Steps advised:** Read `READ_ME_FIRST.txt`, obtain the HTML via GitHub's Download raw file control if necessary, open the saved `.html` via Samsung My Files, and import the fresh GitHub JSON inside MileSage.
- **Status:** Open — wait for actual mobile launch and baseline verification; do not mark a pass.


## 2026-11-13 — Wrong archive opened on phone; corrected package published
- **Observed:** Samsung My Files screenshot at approximately 09:40 local time shows extracted `Vehicle_Manager_Project_Transfer` with `assets/`, `README_FIRST.md`, and `Vehicle_Manager_..._2026-11-06.md`; these are project history/visual references, not the mobile application.
- **Correction:** Published a separate 44,334-byte ZIP at `mobile/MileSage_Alpha_1_1_Mobile_Phone.zip`, containing the actual GitHub mobile HTML preview renamed `MileSage_Mobile.html`, verified fresh-reset `Alpha_1_1_Reset_vehicles.json`, and `READ_ME_FIRST.txt`.
- **Source commit:** `2f048d4362ee9fa544da1eb84c3ac7c40cc6fdd7`.
- **Expected phone steps:** Download that ZIP, extract it, open `MileSage_Mobile.html` in a browser, and manually import from GitHub or choose the included JSON. Confirm Tacoma and Explorer both have zero miles and empty histories.
- **Status:** Package created on GitHub; phone end-to-end launch and import are pending verification.
