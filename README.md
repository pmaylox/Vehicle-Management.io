# Vehick-Management.io

## Current project version

**MileSage Alpha 1.1.1** — source/configuration patch designation (November 14, 2026).

This patch records the Tacoma's user-configured tire-rotation and oil-service interval changes. GitHub configuration and documentation have been updated; an Android APK has **not** been built, published, or verified, and mobile/desktop testing of the patch remains pending. The standalone mobile HTML remains a preview, and devices may retain older locally saved data until deliberately synchronized.

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
