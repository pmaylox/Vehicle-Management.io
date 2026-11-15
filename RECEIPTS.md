# Receipt photos and autofill

Record Fuel, Edit Fuel, Record Service and Edit Service include receipt controls.

1. Take photo opens Windows Camera. Take/save the picture, return to Vehicle Manager, then use Choose photo (usually Pictures / Camera Roll). You can also import a phone photo as JPG, PNG, BMP or TIFF.
2. Choosing a photo starts local Windows OCR. Review the recognized text and selected field proposals, correct them if needed, then Apply selected fields. Nothing is saved automatically.
3. Use the existing Save action after checking the form. Normal date, cost, mileage and fuel validations remain active. Unknown details stay unchanged; full-tank and maintenance reset choices stay manual. Edit dialogs only autofill fields that are already editable.
4. View photo opens the attached image. The attachment is stored when the record saves, under receipts/ using a unique filename. Cancellation does not copy a photo; failed saves roll back the new copy. Replacing or deleting a record does not delete older receipt photos.

Back up the receipts folder together with vehicles.json and vehicles_backup.json; the JSON files contain relative photo references, not image data. Keep receipt_ocr.ps1 beside app.py. Local OCR needs Windows OCR language support and Pillow (already available in the current Python installation). No cloud service, API key, or photo upload is used.

OCR proposes explicitly labeled dates, totals, odometer, gallons, octane, blends, and recognized service descriptions. It can miss unclear or differently formatted receipts. It does not infer fuel suitability, full-tank status or battery warranty details. Service odometer must stay within the tracked vehicle mileage; update the vehicle mileage first if required. A receipt's old service mileage cannot reset a newer maintenance event.

Windows OCR reference: https://learn.microsoft.com/en-us/uwp/api/windows.media.ocr.ocrengine
