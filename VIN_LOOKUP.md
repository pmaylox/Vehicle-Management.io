# VIN lookup and vehicle details

Open Add Vehicle or Edit Vehicle. Enter a full 17-character VIN and choose Look up VIN. This sends that VIN (and the model year if entered) over HTTPS to NHTSA vPIC. An internet connection is required for lookup; no account or API key is required. Lookups run in the background with a timeout.

Review returned year, make/model, trim, series, drive type, engine, fuel, transmission, body style, doors and assembly country. Availability varies. Apply details changes only the form. Existing custom vehicle names are kept by default; the name and year each have a checkbox in review. Odometer and maintenance records are never changed by decoding. Save Vehicle/Save Changes commits the result.

Color and paint code are manual fields; the free decoder does not supply them. Other specification fields remain editable. An unavailable lookup does not stop manual entry. Invalid/unverified decode responses show an error rather than presenting partial guesses as verified results. Historical vehicles without a modern 17-character VIN can leave VIN blank and use manual fields.

Saved profile data is stored with the vehicle in vehicles.json and shown in the Overview Vehicle Details card; it remains available offline. Previous vehicle JSON files load with an empty profile. Fuel/maintenance history is preserved. Duplicate saved VINs are rejected. Save failure restores the previous profile and existing vehicle values.

This is a specification lookup, not an accident/title/ownership report or recall-status lookup. It does not retrieve a vehicle photo. Manufacturer option/build records, VIN-photo scanning and vehicle-photo cards remain separate future features.

Official API documentation: https://vpic.nhtsa.dot.gov/api/
