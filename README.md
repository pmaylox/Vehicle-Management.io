# Vehick-Management.io

## MileSage — configured maintenance intervals

Current user-configured service reminders in [`vehicles.json`](vehicles.json) (updated November 14, 2026):

| Vehicle | Tire rotation interval | Oil-change/service interval |
|---|---:|---:|
| 2026 Toyota Tacoma | 5,000 miles | 10,000 miles |
| 2025 Ford Explorer | 5,000 miles | 5,000 miles |

The Tacoma's tire rotation was changed from 10,000 to 5,000 miles, and its oil-change/service interval from 5,500 to 10,000 miles. These are app settings requested by the vehicle owner, **not a verification of manufacturer recommendations**. The saved odometer and service history are separate from these intervals.

**Phone sync note:** The mobile HTML app keeps local data. A GitHub update does not automatically overwrite phone records. Back up any local phone changes before manually importing GitHub `vehicles.json` from **Data & backup**, since import replaces local records. The update has been verified in GitHub but not yet on the phone.

See [`Alpha 1.1 test log`](testing/alpha-1.1/TEST_LOG.md) for the dated change record and the original reset baseline.
