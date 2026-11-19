'use strict';
// Backup Library: saved local snapshots stay reusable, downloaded JSON backups
// remain selectable via Android's picker, and restores keep import safeguards.
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const paths=['mobile/MileSage_Mobile_Auto_Refresh.html','mobile/MileSage_Alpha_1_3_2_VIN_Lookup.html'];
const pages=paths.map(p=>fs.readFileSync(p,'utf8'));
assert.equal(pages[0],pages[1]);
for(const page of pages){
 assert.equal(page.split('</body></html>').length,2,'No duplicated HTML');
 assert.equal(page.split('function showSavedBackupLibrary(){').length,2);
 assert.ok(page.includes('id="savedBackupLibrary"'));
 assert.ok(page.includes('id="browseSavedJson"'));
 assert.ok(page.includes('id="savedLocalSnapshots"'));
 assert.ok(page.includes('Saved backups &amp; snapshots'));
 assert.ok(!page.includes('Remove the original snapshot once used'),'Snapshot must not be consumed');
 assert.ok(page.includes("$('jsonFile').value='';"),'Allow selecting the same downloaded file again');
 assert.ok(page.includes('const accepted=replace({format:'),'Use same safe import guards');
 new vm.Script(page.split('<script>')[1].split('</script>')[0]);
 const body=page.match(/\/\* REUSABLE_BACKUP_LIBRARY_BEGIN \*\/[\s\S]*?\/\* REUSABLE_BACKUP_LIBRARY_END \*\//)?.[0];
 assert.ok(body,'Backup Library logic missing');
 let fileClicks=0,restores=0;
 const now=[{created_at:'2026-11-17T10:00:00Z',vehicles:[{name:'A'}],current:0},
 {created_at:'2026-11-16T10:00:00Z',vehicles:[{name:'B'}],current:0},
 {created_at:'2026-11-15T10:00:00Z',vehicles:[{name:'C'}],current:0}];
 const holder={list:now};
 const nodes={
  savedLocalSnapshots:{innerHTML:'',querySelectorAll:()=>[]},
  jsonImportStatus:{textContent:''},
  jsonFile:{value:'selected-once',click:()=>{fileClicks++;}},
  savedBackupLibrary:{hidden:true},
  savedBackupStatus:{textContent:''}
 };
 const ctx={
  $:id=>nodes[id],
  readSnapshots:()=>holder.list,
  localStorage:{setItem:(key,value)=>{holder.list=JSON.parse(value);}},
  RECOVERY_KEY:'recovery-test',
  JSON,Number,Date,String,
  esc:x=>String(x).replaceAll('&','&amp;').replaceAll('<','&lt;'),
  alert:()=>{throw Error('Unexpected alert');},
  confirm:()=>true,message:()=>{},
  replace:payload=>{
   restores++;
   assert.equal(payload.vehicles[0].name, 'C','Restore should choose oldest snapshot');
   // Simulate preservePreImport trimming list to 3, which would drop C.
   holder.list=[{created_at:'2026-11-19T12:00:00Z',vehicles:[{name:'NOW'}],current:0},
      ...holder.list].slice(0,3);
   return true;
  }
 };
 vm.runInNewContext(body,ctx);
 ctx.showSavedBackupLibrary();
 assert.equal(nodes.savedBackupLibrary.hidden,false);
 assert.ok(nodes.savedLocalSnapshots.innerHTML.includes('Review &amp; restore')===false);
 assert.ok(nodes.savedLocalSnapshots.innerHTML.includes('Review & restore'));
 ctx.openBackupFilePicker();ctx.openBackupFilePicker();
 assert.equal(fileClicks,2,'Downloaded JSON picker can be reopened');
 assert.equal(nodes.jsonFile.value,'','Re-select identical JSON file');
 assert.ok(nodes.jsonImportStatus.textContent.includes('Downloads > MileSage'));
 assert.equal(ctx.restoreSavedSnapshot(2),true);
 assert.equal(restores,1);
 assert.ok(holder.list.some(x=>x.created_at==='2026-11-15T10:00:00Z'),
   'Previously used oldest snapshot must remain available after restore');
 assert.ok(holder.list.length<=3);
 const reuseIndex=holder.list.findIndex(x=>x.created_at==='2026-11-15T10:00:00Z');
 // The stub still models a replacement/backup creation, check repeated access.
 assert.ok(reuseIndex>=0);
}
const gradle=fs.readFileSync('android/app/build.gradle','utf8');
assert.match(gradle,/applicationId 'io\.reddirtcode\.milesage\.alpha146pdfimport'/);
console.log('PASS: backup picker reusable, saved snapshots visible and oldest snapshot retained after restore.');
