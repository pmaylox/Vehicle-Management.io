// Alpha 1.4.1 single-page Service receipt OCR regression.
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const htmlFiles=['mobile/MileSage_Mobile_Auto_Refresh.html','mobile/MileSage_Alpha_1_3_2_VIN_Lookup.html'];
const java=fs.readFileSync('android/app/src/main/java/io/reddirtcode/milesage/MainActivity.java','utf8');
for(const text of [
 'SERVICE_RECEIPT_SCAN_CODE','serviceReceiptScanOpen',
 'GmsDocumentScannerOptions.RESULT_FORMAT_JPEG','setPageLimit(1)',
 'InputImage.fromFilePath(this, receipt)', 'serviceReceiptScanResult(found.getText(), fuelScanPreview(receipt), null)',
 'window.milesageServiceReceiptComplete','@JavascriptInterface public void scanServiceReceipt()',
 'setPageLimit(30)','GmsDocumentScannerOptions.RESULT_FORMAT_PDF',
 '@JavascriptInterface public void scanServiceInvoice()'
])assert.ok(java.includes(text),'Missing native Service scan feature: '+text);
const build=fs.readFileSync('android/app/build.gradle','utf8');
assert.match(build,/applicationId 'io\.reddirtcode\.milesage\.alpha142expensepdf'/);
for (const path of htmlFiles){
 const html=fs.readFileSync(path,'utf8');
 assert.ok(html.includes('SERVICE_RECEIPT_V2_BEGIN'),path);
 for(const required of ["window.milesageServiceReceiptComplete=async function",
   "window.MileSageAndroid.scanServiceReceipt()","showReceiptPreview('service',file)",
   "if(epoch!==serviceDraftEpoch||v()!==owner)return;",
   "serviceReceiptScanOwner=null;serviceReceiptScanEpoch=null;",
   "function applyServiceScanV2(raw,a,origin)",
   "storeReceipt(a,'service'",'scanServicePdf','service_document'])
   assert.ok(html.includes(required),path+' missing '+required);
 const section=html.match(/function parseServiceReceiptText\(raw,today\)\{[\s\S]*?\n\}\n\/\* RECEIPT_PARSER_END \*\//)?.[0];
 assert.ok(section,'No service OCR parser');
 const ctx={Date};
 vm.runInNewContext(section+'\nthis.parse=parseServiceReceiptText;',ctx);
 const found=ctx.parse('REPAIR INVOICE\nINVOICE DATE 11/14/2026\nODO 4560\nSynthetic oil change\nTire rotation\nTOTAL PAID $127.90','2026-11-18');
 assert.equal(found.date,'2026-11-14');
 assert.equal(found.mileage,4560);
 assert.equal(found.cost,'127.90');
 assert.equal(found.oil,true);
 assert.equal(found.tire,true);
 const noInvoice=ctx.parse('THANK YOU FOR YOUR BUSINESS','2026-11-18');
 assert.equal(noInvoice.date,null);
 assert.equal(noInvoice.cost,null);
 assert.equal(noInvoice.oil,false);
}
console.log('PASS: native one-page service receipt OCR, parser, preview, cancel and independent PDF scanner.');
