'use strict';
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const path=require('node:path');
const files=['mobile/MileSage_Mobile_Auto_Refresh.html','mobile/MileSage_Alpha_1_3_2_VIN_Lookup.html'];
const htmls=files.map(p=>fs.readFileSync(p,'utf8'));
assert.equal(htmls[0],htmls[1],'Both distributed mobile HTML files must match');
const java=fs.readFileSync('android/app/src/main/java/io/reddirtcode/milesage/MainActivity.java','utf8');
const build=fs.readFileSync('android/app/build.gradle','utf8');
const provider=fs.readFileSync('android/app/src/main/res/xml/file_paths.xml','utf8');
for(const html of htmls){
 const code=html.split('<script>')[1].split('</script>')[0];
 new vm.Script(code);
 for(const required of ['id="scanServicePdf"','servicePdfScanStatus','servicePdfPreview',
    'window.milesageServiceScannerComplete','wireServicePdfScanner(a)',
    'wireServicePdfHistory();','record.service_document={',
    'View scanned invoice','Share / backup PDF','servicePdfDraft=null']){
  assert.ok(html.includes(required),'Missing service scanner integration: '+required);
 }
 assert.ok(html.includes("wireFuelReceiptPhoto(a)"),'Existing fuel photo UI must remain intact');
 assert.ok(html.includes('function parseGallonsInput('),'Combined build must include the fuel precision fix');
 const fuelStart=html.indexOf('function renderFuel()');
 const fuelEnd=html.indexOf('function expenseSummary(',fuelStart);
 assert.ok(fuelStart>0&&fuelEnd>fuelStart);
 assert.ok(!html.slice(fuelStart,fuelEnd).includes('scanServicePdf'),'Multi-page button must not appear in Fuel');
 const snippet=code.split('/* SERVICE_MULTIPAGE_PDF_BEGIN */')[1].split('/* SERVICE_MULTIPAGE_PDF_END */')[0];
 assert.ok(snippet.includes('servicePdfDraft={vehicle:'),'A scanned PDF must bind to the chosen vehicle');
 assert.ok(snippet.includes('if(v()!==servicePdfScanOwner)'),'Reject result for changed vehicle');
}
for(const fragment of [
 'GmsDocumentScanning.getClient(options)',
 'setPageLimit(30)',
 'GmsDocumentScannerOptions.RESULT_FORMAT_PDF',
 'startIntentSenderForResult(intentSender, SERVICE_DOCUMENT_SCAN_CODE',
 'GmsDocumentScanningResult.fromActivityResultIntent(data)',
 'getFilesDir(), "service_invoices"',
 'serviceScanResult(payload, null)',
 '@JavascriptInterface public void scanServiceInvoice()',
 '@JavascriptInterface public void openServiceInvoice(String id)',
 '@JavascriptInterface public void shareServiceInvoice(String id)',
 'FLAG_GRANT_READ_URI_PERMISSION'
])assert.ok(java.includes(fragment),'Missing native scanner part: '+fragment);
assert.ok(provider.includes('name="service_invoices" path="service_invoices/"'),
 'The app-private PDF folder must be accessible through FileProvider');
assert.ok(build.includes('play-services-mlkit-document-scanner:16.0.0'));
assert.ok(build.includes('com.google.mlkit:text-recognition:16.0.1'),
 'Offline Android receipt OCR library must remain bundled');
assert.ok(java.includes('@JavascriptInterface public void recognizeReceipt(String requestId, String base64)'),
 'Native on-device OCR must remain connected to the receipt photo UI');
assert.ok(build.includes("applicationId 'io.reddirtcode.milesage.alpha139ocrtest'"),
 'Alpha 1.3.9 OCR test must install separately from previous MileSage alpha test apps');
assert.ok(!build.includes("applicationId 'io.reddirtcode.milesage.alpha137repair'"),
 'Never reuse the prior Repair Test identity with a different debug signing certificate');
console.log('PASS: Service multi-page PDF, Fuel autofill/3-decimal, native hooks, Fuel scan isolation, JS syntax.');
