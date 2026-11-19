'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm');
const files=['mobile/MileSage_Mobile_Auto_Refresh.html','mobile/MileSage_Alpha_1_3_2_VIN_Lookup.html'];
const [first,second]=files.map(f=>fs.readFileSync(f,'utf8'));
assert.equal(first,second,'Both mobile HTML distributions must match');
for(const html of [first,second]){
 assert.equal(html.split('</body></html>').length,2,'Duplicate document tail not allowed');
 assert.equal(html.split('function renderExpenses(){').length,2,'Only one expense renderer');
 const script=html.split('<script>')[1]?.split('</script>')[0];
 new vm.Script(script);
 const shared=script.match(/function parseServiceReceiptText\(raw,today\)\{[\s\S]*?\/\* RECEIPT_PARSER_END \*\//)?.[0];
 const receipt=script.match(/\/\* EXPENSE_PDF_OCR_BEGIN \*\/([\s\S]*?)\/\* EXPENSE_PDF_OCR_END \*\//)?.[1];
 assert.ok(shared&&receipt,'Missing OCR parser');
 const ctx={Date};
 vm.runInNewContext(shared+'\n'+receipt+'\nthis.read=parseExpenseDocumentText;',ctx);
 const read=s=>ctx.read(s,'2026-11-19');
 const result=read('--- PAGE 1 ---\nBODY REPAIR ESTIMATE\nINVOICE DATE 11/14/2026\nCOLLISION CENTER\nBUMPER $350.00\nPARTS TOTAL $350.00\n--- PAGE 2 ---\nLabor $600.00\nSales Tax $90.00\n--- PAGE 3 ---\nFINAL ESTIMATE\nTOTAL REPAIR COST $1,500.75');
 assert.equal(result.date,'2026-11-14');
 assert.equal(result.cost,'1500.75');
 assert.equal(result.description,'Body repair estimate');
 assert.equal(result.conflict,false);
 const duplicate=read('Invoice date 11/18/26\nGRAND TOTAL $3,218.50\n--- PAGE 2 ---\nINVOICE TOTAL $3,218.50');
 assert.equal(duplicate.cost,'3218.50','Identical totals across pages can be used');
 const conflict=read('GRAND TOTAL $1,500.75\n--- PAGE 3 ---\nTOTAL DUE $1,700.00');
 assert.equal(conflict.cost,null,'Conflicting totals must remain blank');
 assert.equal(conflict.conflict,true);
 assert.equal(read('PARTS TOTAL $950.00\nLABOR TOTAL $700.00').cost,null);
 assert.equal(read('TOTAL $2,200.00').cost,null,'Generic total alone is unsafe');
 assert.ok(html.includes('window.milesageExpenseOCRComplete=function(result)'));
 assert.ok(html.includes("baseline.cost===''"),'Do not replace manually entered expense');
 assert.ok(html.includes("draft.epoch!==expensePhotoDraftEpoch"),'Discard stale OCR');
 assert.ok(html.includes('data-expense-pdf-save='));
 for(const q of ['id="expensePdfActions"','id="saveExpensePdfDraft"','id="viewExpensePdfDraft"',
  'id="shareExpensePdfDraft"','id="expensePdfTextReview"'])
  assert.ok(html.includes(q),'Missing expense PDF control: '+q);
}
const java=fs.readFileSync('android/app/src/main/java/io/reddirtcode/milesage/MainActivity.java','utf8');
for(const q of [
 'GmsDocumentScannerOptions.RESULT_FORMAT_PDF, GmsDocumentScannerOptions.RESULT_FORMAT_JPEG',
 'beginExpensePagesOCR(scan.getPages(), id)',
 'private void recognizeExpensePage(', 'recognizer.process(image)',
 'private void expenseOcrResult(', 'window.milesageExpenseOCRComplete',
 'private void exportExpenseDocument(String id)', 'MediaStore.Downloads.EXTERNAL_CONTENT_URI',
 'Environment.DIRECTORY_DOWNLOADS + "/MileSage/Expenses"',
 '@JavascriptInterface public void saveExpenseDocument(String id)',
 'SERVICE_DOCUMENT_SCAN_CODE','FUEL_DOCUMENT_SCAN_CODE'])
 assert.ok(java.includes(q),'Missing native PDF/OCR/export: '+q);
console.log('PASS: expense multi-page OCR, safe totals, finding PDFs, manual edits and valid HTML');
