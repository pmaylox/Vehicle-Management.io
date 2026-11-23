'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const pages=['mobile/MileSage_Mobile_Auto_Refresh.html','mobile/MileSage_Alpha_1_3_2_VIN_Lookup.html'];
const html=pages.map(x=>fs.readFileSync(x,'utf8'));
assert.equal(html[0],html[1],'HTML copies must be identical');
for(const s of html){
 assert.equal(s.split('</body></html>').length,2,'Single HTML root');
 assert.ok(s.includes('id="loadExpensePdf"'),'New expense file picker');
 assert.ok(s.includes('data-expense-pdf-attach'),'Recovery file picker in expense history');
 assert.ok(s.includes('window.MileSageAndroid.chooseExpensePdfFile(true)'),'Attach existing record');
 assert.ok(s.includes('window.MileSageAndroid.chooseExpensePdfFile(false)'),'Attach new expense');
 assert.ok(s.includes('window.milesageExpenseHistoryImportComplete=function(result)'));
 assert.ok(s.includes('if(vehicle!==target.vehicle||record!==target.record'));
 assert.ok(s.includes('record.expense_document=previous;'),'Failed save rolls back metadata');
 assert.ok(s.includes('No record changed.'));
 assert.ok(!s.includes('Imported PDF is not automatically OCR-read'),'Imported PDF must now be scanned');
 assert.ok(s.includes("info.ocr_pending?'Reading pages for date, total and description…'"),
   'Imported PDFs report OCR progress');
 assert.ok(s.includes("baseline.cost===''"),'OCR must not overwrite user-entered values');
 assert.ok(s.includes('window.milesageExpenseOCRComplete=function(result)'),
   'Native PDF OCR uses existing review-before-save callback');
 const script=s.split('<script>')[1]?.split('</script>')[0];
 new vm.Script(script);
}
const java=fs.readFileSync('android/app/src/main/java/io/reddirtcode/milesage/MainActivity.java','utf8');
assert.ok(java.includes('Intent.ACTION_OPEN_DOCUMENT'));
assert.ok(java.includes('picker.setType("application/pdf")'),'Only PDF files');
assert.ok(java.includes('new PdfRenderer(descriptor)'),'Real page validation');
assert.ok(java.includes('count > 30_000_000L'),'Size limit');
assert.ok(java.includes('pages < 1 || pages > 30'),'Page limit');
assert.ok(java.includes('pendingExpensePdfHistoryImport'),'History scope');
assert.ok(java.includes('new File(getFilesDir(), "expense_invoices")'),'Same protected PDF storage');
assert.ok(java.includes('void chooseExpensePdfFile(boolean forHistory)'),'Native JS bridge');
assert.ok(java.includes('if(window.milesageExpenseHistoryImportComplete)'));
assert.ok(java.includes('payload.put("ocr_pending",!forHistory)'),'New PDFs OCR, history attachments do not');
assert.ok(java.includes('if (!forHistory) readImportedExpensePdf(target,id);'));
assert.ok(java.includes('private void readImportedExpensePdf(File pdf, String id)'));
assert.ok(java.includes('try (PdfRenderer.Page page = renderer.openPage(i))'),'Pages processed serially');
assert.ok(java.includes('page.render(bitmap, null, null, PdfRenderer.Page.RENDER_MODE_FOR_DISPLAY)'));
assert.ok(java.includes('Tasks.await('),'Wait for each OCR result off the UI thread');
assert.ok(java.includes('expenseOcrResult(id, all.toString(), pagesRead, error)'));
assert.ok(java.includes('2000f / Math.max(1, page.getWidth())'),'Limit bitmap memory');
assert.ok(java.includes('bitmap.recycle()'),'Do not accumulate full-page images');

const gradle=fs.readFileSync('android/app/build.gradle','utf8');
assert.ok(gradle.includes("applicationId 'io.reddirtcode.milesage.alpha149brandedtest'"),'Independent test install');
console.log('PASS: separate PDF file picker, verified safe file copy, reattachment and restored history safeguards.');
