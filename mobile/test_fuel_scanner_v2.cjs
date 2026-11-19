// Fuel Scanner V2 tests: run node mobile/test_fuel_scanner_v2.cjs
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
for(const file of ['mobile/MileSage_Mobile_Auto_Refresh.html',
 'mobile/MileSage_Alpha_1_3_2_VIN_Lookup.html']){
 const html=fs.readFileSync(file,'utf8');
 const m=html.match(/\/\* FUEL_SCANNER_V2_BEGIN \*\/([\s\S]*?)\/\* FUEL_SCANNER_V2_END \*\//);
 assert.ok(m, file+' missing scanner parser');
 assert.match(html,/window\.milesageFuelScanComplete=async function/);
 assert.match(html,/MileSageAndroid\.scanFuelReceipt\(\)/);
 assert.match(html,/showReceiptPreview\('fuel',file\)/);
 const ctx={parseServiceReceiptText:()=>({date:null,mileage:null})};
 vm.runInNewContext(m[1]+'\nthis.scan=parseFuelScanV2;',ctx,{filename:file});
 const scan=raw=>ctx.scan(raw,'2026-11-18');
 let found=scan("WELCOME ALLSUPS\nDATE 11/16/26\nGALLONS 10.882\nPRICE / GAL $3.599\nFUEL SALE $39.16\nTHANK YOU");
 assert.equal(found.gallons,'10.882');
 assert.equal(found.total,'39.16');
 assert.equal(found.unitPrice,'3.599');
 assert.equal(found.verified,true);
 found=scan("ALLSUPS\nPRODUCT: UNL 10.882\nGALL0NS: $3.599\nFUEL 5ALE: $39.16");
 assert.equal(found.gallons,'10.882','OCR-shifted row volume');
 assert.equal(found.total,'39.16','OCR-shifted row total');
 assert.equal(found.verified,true);
 found=scan("UNLEADED\n10.882\n$3.599\n$39.16");
 assert.equal(found.gallons,'10.882','number-only OCR checked with arithmetic');
 assert.equal(found.total,'39.16');
 assert.equal(found.verified,true);
 found=scan("GALLONS 10.882\nPRICE / GAL $3.599\nFUEL SALE $49.16");
 assert.equal(found.verified,false,'mismatched arithmetic is never called verified');
 assert.equal(found.conflict,true,'mismatched total must raise conflict');
 assert.equal(found.gallons,null,'mismatched total cannot autofill gallons');
 assert.equal(found.total,null,'mismatched total cannot autofill payment');
 found=scan("PRICE / GAL $3.599\nACCOUNT 123456789\nVISA ******** 9943");
 assert.equal(found.gallons,null,'price is not gallons');
 assert.equal(found.total,null,'card number is not total');
 found=scan("PRODUCT UNLEADED\nGALLONS 12.500\nFUEL SALE $42.85");
 assert.equal(found.gallons,'12.500','explicit label is safe');
 assert.equal(found.total,'42.85','explicit total is safe');
 assert.equal(found.verified,false,'no price, no arithmetic verification');
}
const java=fs.readFileSync('android/app/src/main/java/io/reddirtcode/milesage/MainActivity.java','utf8');
for (const phrase of ['FUEL_DOCUMENT_SCAN_CODE','setPageLimit(1)',
 'RESULT_FORMAT_JPEG','SCANNER_MODE_FULL','fuelScanPreview(receipt)',
 'InputImage.fromFilePath(this, receipt)','scanFuelReceipt()',
 'window.milesageFuelScanComplete']) {
 assert.ok(java.includes(phrase),'Missing native scanner: '+phrase);
}
assert.ok(java.includes('SERVICE_DOCUMENT_SCAN_CODE'),'Service PDF scanner must remain');
console.log('Fuel Scanner V2 crop/OCR/verified parser regression tests passed');
