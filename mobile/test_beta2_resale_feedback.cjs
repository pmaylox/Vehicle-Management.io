'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const files=['mobile/MileSage_Mobile_Auto_Refresh.html','mobile/MileSage_Alpha_1_3_2_VIN_Lookup.html'];
const pages=files.map(x=>fs.readFileSync(x,'utf8'));
assert.equal(pages[0],pages[1]);
for(const html of pages){
 assert.ok(html.includes('BETA2_RESALE_FEEDBACK_BEGIN'));
 assert.ok(html.includes('id="betaFeedbackBody"'));
 assert.ok(html.includes('function resaleCard(a)'));
 assert.ok(html.includes('function wireFeedbackPanel()'));
 assert.ok(html.includes('saveFeedbackRecords(items)'));
 assert.ok(html.includes('a.resale_valuations.push('));
 assert.ok(html.includes('Kelley Blue Book'));
 assert.ok(html.includes('No vehicle records, VIN, receipt photos or PDFs are attached automatically.'));
 assert.ok(html.includes("navigator.share({title:'MileSage beta feedback',text})"));
 assert.ok(html.includes('renderGraphs();message(\'Resale valuation recorded.\')'));
 new vm.Script(html.split('<script>')[1].split('</script>')[0]);
}
const g=fs.readFileSync('android/app/build.gradle','utf8');
assert.match(g,/applicationId 'io\.reddirtcode\.milesage\.alpha146pdfimport'/);
assert.match(g,/versionCode 147/);
console.log('PASS: beta feedback, consent-based sharing, vehicle resale snapshots, and distinct test APK.');
