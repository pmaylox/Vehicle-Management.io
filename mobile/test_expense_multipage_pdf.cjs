'use strict';
// Alpha 1.4.5 regression: Expenses PDF scanner never changes Service PDF or
// receipt-photo behavior, and no expense is stored until explicit Save.
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const paths=['mobile/MileSage_Mobile_Auto_Refresh.html',
             'mobile/MileSage_Alpha_1_3_2_VIN_Lookup.html'];
const htmls=paths.map(p=>fs.readFileSync(p,'utf8'));
assert.equal(htmls[0],htmls[1]);
for(const html of htmls){
 new vm.Script(html.split('<script>')[1].split('</script>')[0]);
 for (const required of [
  '/* EXPENSE_MULTIPAGE_PDF_BEGIN */',
  'id="scanExpensePdf"','id="clearExpensePdf"','id="expensePdfPreview"',
  'id="viewExpensePdfDraft"','id="shareExpensePdfDraft"','id="saveExpensePdfDraft"',
  'window.milesageExpenseScannerComplete=function(result)',
  'window.milesageExpenseOCRComplete=function(result)',
  "typeof window.MileSageAndroid?.scanExpenseDocument!=='function'",
  'expensePdfDraft={vehicle:owner,id:info.id,pages:info.pages,',
  'record.expense_document={id:pdf.id,pages:pdf.pages,name:pdf.name}',
  "wireExpensePdfScanner(a);wireExpensePdfHistory();",
  "data-expense-pdf=\"'+index+'\"",
  "data-expense-pdf-share=\"'+index+'\"",
  "data-expense-pdf-save=\"'+index+'\"",
  'window.MileSageAndroid.openExpenseDocument(doc.id)',
  'window.MileSageAndroid.shareExpenseDocument(doc.id)',
  'window.MileSageAndroid.saveExpenseDocument(doc.id)',
  "if(pdf){expensePdfDraft=null;renderExpenses();}",
  'Full mobile JSON backup does not include PDF files.',
  "storeReceipt(a,'expense',record,()=>a.mobile_expenses.push(record));",
  'wireServicePdfScanner(a);wireServicePdfHistory();',
  "showReceiptPreview('expense',file)"
 ])assert.ok(html.includes(required),'Expense PDF missing '+required);
 const idx=html.indexOf('function renderExpenses(){');
 assert.ok(idx>0);
 const part=html.slice(idx,html.indexOf('function mpgSeries(',idx));
 assert.ok(part.includes("if(pdf)record.expense_document"),'PDF attached only to expense record');
 assert.ok(!part.includes('a.service_history.push('),'Expense must not modify service');
}
const java=fs.readFileSync('android/app/src/main/java/io/reddirtcode/milesage/MainActivity.java','utf8');
for(const required of [
 'EXPENSE_DOCUMENT_SCAN_CODE = 222','if (requestCode == EXPENSE_DOCUMENT_SCAN_CODE)',
 'expenseScanOpen = false','setPageLimit(30)',
 'GmsDocumentScannerOptions.RESULT_FORMAT_PDF',
 'getFilesDir(), "expense_invoices"',
 'if (total > 30_000_000) throw new IOException("PDF exceeds 30 MB.")',
 'MileSage-Expense-',
 'expenseScanResult(payload, null)',
 'beginExpensePagesOCR(scan.getPages(), id)',
 'window.milesageExpenseOCRComplete',
 'exportExpenseDocument(String id)',
 'MediaStore.MediaColumns.RELATIVE_PATH',
 'Environment.DIRECTORY_DOWNLOADS + "/MileSage/Expenses"',
 'GmsDocumentScannerOptions.RESULT_FORMAT_PDF, GmsDocumentScannerOptions.RESULT_FORMAT_JPEG',
 'window.milesageExpenseScannerComplete',
 'beginExpenseDocumentScan()',
 '@JavascriptInterface public void scanExpenseDocument()',
 '@JavascriptInterface public void openExpenseDocument(String id)',
 '@JavascriptInterface public void shareExpenseDocument(String id)',
 'FileProvider.getUriForFile(this, getPackageName() + ".fileprovider", file)',
 'getFilesDir(), "service_invoices"',
 'SERVICE_DOCUMENT_SCAN_CODE'
])assert.ok(java.includes(required),'Missing native expense PDF support: '+required);
const provider=fs.readFileSync('android/app/src/main/res/xml/file_paths.xml','utf8');
for(const name of ['service_invoices','expense_invoices'])
 assert.ok(provider.includes('name="'+name+'" path="'+name+'/"'),
  'FileProvider missing '+name);
const gradle=fs.readFileSync('android/app/build.gradle','utf8');
assert.ok(gradle.includes("applicationId 'io.reddirtcode.milesage.alpha145testers'"),
 'Alpha 1.4.5 must install separately and never overwrite existing vehicle records');
console.log('PASS: 30-page Expense PDF capture, persistence reference, view/share, Service isolation and build identity.');
