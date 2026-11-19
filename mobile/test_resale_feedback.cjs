'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const paths=['mobile/MileSage_Mobile_Auto_Refresh.html','mobile/MileSage_Alpha_1_3_2_VIN_Lookup.html'];
const [html,mirror]=paths.map(f=>fs.readFileSync(f,'utf8'));
assert.equal(html,mirror,'Both distributed mobile builds must match');
assert.equal(html.split('</body></html>').length,2,'HTML must not be duplicated');
assert.ok(html.includes('const SECOND_TESTER_BUILD=true;'),'Test build must disable developer data imports');
for(const id of ['resaleTrade','resalePrivate','resaleNotes','feedbackTitle','feedbackContact'])
 assert.ok(html.includes('id="'+id+'" type="text"'),'Text field must use block input CSS: '+id);
assert.ok(html.includes('id="githubBackupRecovery" class="btn" type="button" hidden disabled'),'Developer recovery must be hidden and disabled');
assert.ok(html.includes('id="githubImport" class="btn secondary" type="button" hidden disabled'),'Developer GitHub import must be hidden and disabled');
assert.ok(html.includes("if(SECOND_TESTER_BUILD){syncStatus='Tester build:"),'Remote refresh must exit before fetching developer records');
const script=html.split('<script>')[1]?.split('</script>')[0];
new vm.Script(script);
for(const required of [
 '/* RESALE_TRACKER_BEGIN */','/* TESTER_FEEDBACK_BEGIN */',
 'id="lookupKBB"','id="resaleForm"','id="feedbackForm"',
 'id="feedbackShortcut"','id="feedbackFromData"',
 'id="feedbackType"','id="feedbackSeverity"',
 'id="feedbackDetails"','id="feedbackHistory"',
 'id="saveFeedbackOnly"','id="feedbackExport"',
 "FEEDBACK_KEY='milesage-alpha145-tester-feedback-v1'",
 "window.MileSageAndroid.shareTesterFeedback(content)",
 "if(!validDate(date)||mileage>9999999)",
 "resale_history:Array.isArray(x.resale_history)?x.resale_history:[]",
 "resale_history,...obj"
])assert.ok(html.includes(required),'Missing feature '+required);
const resale=script.match(/\/\* RESALE_TRACKER_BEGIN \*\/([\s\S]*?)\/\* RESALE_TRACKER_END \*\//)?.[1];
assert.ok(resale,'Resale helper missing');
const ctx={Number,Math,Array,String,Date,
 esc:x=>String(x),num:x=>Number(x).toLocaleString('en-US'),
 usd:x=>'$'+(Number(x)/100).toFixed(2),
 localDate:()=> '2026-11-19'};
vm.runInNewContext(resale+'\nthis.rows=resaleRows;this.graph=resaleGraph;this.card=resaleCard;',ctx);
const tacoma={name:'Toyota Tacoma',mileage:4790,resale_history:[
 {date:'2026-11-05',mileage:4000,trade_in_cents:3200000,private_party_cents:3500000,source:'Kelley Blue Book (manual)',condition:'Good'},
 {date:'2026-11-18',mileage:4750,trade_in_cents:3150000,private_party_cents:3400000,source:'Dealer offer',condition:'Good'}
]};
const explorer={name:'Ford Explorer',mileage:12000,resale_history:[]};
assert.equal(ctx.rows(tacoma).length,2);
assert.equal(ctx.rows(explorer).length,0,'Values must be isolated to each vehicle');
assert.ok(ctx.graph(ctx.rows(tacoma)).includes('Trade-in'));
assert.ok(ctx.graph(ctx.rows(tacoma)).includes('Private party'));
assert.ok(ctx.card(tacoma).includes('4,790'));
assert.ok(ctx.card(tacoma).includes('the value has not been recalculated'),
 'Odometer changes must not fabricate current value');
assert.ok(ctx.card(explorer).includes('No recorded valuations yet'));
const java=fs.readFileSync('android/app/src/main/java/io/reddirtcode/milesage/MainActivity.java','utf8');
for(const text of ['@JavascriptInterface public void shareTesterFeedback(String report)',
 '@JavascriptInterface public void openResaleValuation()',
 'Intent.ACTION_SEND','Intent.EXTRA_TEXT','Intent.createChooser',
 'https://www.kbb.com/whats-my-car-worth/'])
 assert.ok(java.includes(text),'Native tester support missing '+text);
const gradle=fs.readFileSync('android/app/build.gradle','utf8');
assert.ok(gradle.includes("applicationId 'io.reddirtcode.milesage.alpha145testers'"),
 'Tester APK must install separately from alpha 1.4.4');
console.log('PASS: resale history and graph by vehicle, no invented KBB quote, Android feedback share, isolated tester APK.');
