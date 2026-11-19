# MileSage — Car History (Alpha 1.3.3 preview)

**Status:** Source feature on a development branch. This is not a CARFAX API integration, an Android APK or a deployed update to an existing phone installation.

## Separate tab

- Mobile: the bottom navigation has a new **Car History** tab, in addition to Home, Service, Fuel, Expenses and Graphs.
- Desktop: a new **Car History** notebook tab and side-navigation button.
- Car History is specific to the selected vehicle: Toyota Tacoma, Ford Explorer, or any other vehicle.
- Optional VIN is displayed on mobile; the feature does not require a VIN.

## CARFAX account and annual reminder

1. In **Car History**, select the vehicle and choose **Open CARFAX Car Care**. This opens the official `https://www.carfax.com/Service` website, not a background API.
2. Read the history that is available to your own CARFAX account; CARFAX's reporting coverage may be incomplete.
3. Return to MileSage and choose the review date and source. Optionally add notes, then tap **Mark history reviewed**.
4. MileSage displays last review, next anniversary and **Annual review due** once the anniversary is reached. Without a previous review, it displays **Review now**.
5. A Home quick action links to Car History and indicates when review is due. No network, purchase, notification permission or automatic retrieval is required.

Calendar rule: review on February 29, 2024 means the next review is due February 28, 2025. The date moves only after the user confirms another review.

## Reported findings

Car History accepts individually entered events: accident/damage, title/registration, ownership, odometer, service, recall and other. Each entry has a date, category, source, optional reported odometer and details. The user can delete an entry after confirmation. Entries are labelled user-entered and are not independently verified.

**Isolation:** Even an odometer value greater than the active vehicle mileage is just a reported historical value. It never edits the actual odometer, fuel history, service records, maintenance countdowns, costs, or the second vehicle. Service history is not automatically merged or duplicated.

The feature does not scan, store, purchase, sync or reproduce CARFAX PDFs. Only user-entered summaries and confirmation metadata are saved. A future licensed CARFAX integration is a separate project.

## Storage and backup

Each vehicle's `car_history` object uses:

```json
{
  "last_review_date": null,
  "review_source": "",
  "review_notes": "",
  "events": []
}
```

For each event: `date`, `category`, `description`, `source`, `mileage` (optional), `recorded_by: "user"`.

- Mobile data is stored in its existing local JSON state and included in **Full mobile backup** and **Export vehicles.json**.
- Desktop `Vehicle.to_dict()` and `Vehicle.from_dict()` save and load the same structure.
- Legacy JSON records without `car_history` load with an empty history.
- Unsafe restore previews warn if imported JSON would remove Car History events or clear a review date. Recovery can fill empty histories from a compatible backup.
- Do not commit actual personal VIN-specific reports or real vehicle histories to a public repository.

## Phone preview only — do not overwrite current APK

A ZIP/HTML preview build can be produced by GitHub Actions **Package MileSage phone HTML**. Its HTML file is `mobile/MileSage_Alpha_1_3_3_Car_History.html` and the maintained entrypoint is `mobile/MileSage_Mobile_Auto_Refresh.html`.

Before opening the preview on a phone: export **Full mobile backup** from the currently installed app; do **not** uninstall the APK, clear its storage, or import public demo `vehicles.json` over personal data. The preview may use a different browser storage origin. Import your own backup into it, then verify both vehicles, odometers, tire pressures, fuel/service records and Car History.

## Tests

```shell
python -m unittest -v test_car_history.py
node mobile/test_car_history.cjs
```

The CI pull-request workflow also checks Python syntax, phone JS syntax and existing MileSage regression tests. Manual browser/desktop testing and Android APK integration are still required before a production release.
