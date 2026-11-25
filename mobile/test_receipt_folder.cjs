// Run: node mobile/test_receipt_folder.cjs
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const html=fs.readFileSync('mobile/MileSage_Mobile_Auto_Refresh.html','utf8');
for(const phrase of [
 'function choosePhotoDir()','showDirectoryPicker({mode:',
 "getDirectoryHandle('MileSage',{create:true})","getDirectoryHandle('Photos',{create:true})",
 'function writePhonePhoto(p)', 'createWritable()', 'function downloadPhonePhoto(p)',
 "storeReceipt(a,'expense'", "storeReceipt(a,'fuel'", "storeReceipt(a,'service'",
 "wirePhotoHistory('expense')", "wirePhotoHistory('fuel')", "wirePhotoHistory('service')",
 "data_url:await photoData(file)",
 'Entry NOT saved. Phone storage failed:',
 'data-photo-save', 'data-photo-download',
 "id=\"choosePhotoDir\"",
 "const KEY='milesage-mobile-offline-v1'"
])assert.ok(html.includes(phrase),'Missing receipt photo safeguard: '+phrase);
assert.match(html,/function recordList[\s\S]*?photoHistory\(r,kind,index\)/);
const code=html.match(/<script>([\s\S]*?)<\/script>/)?.[1];
assert.ok(code);
new vm.Script(code);
const pure=html.match(/function photoBlob\(p\)\{[\s\S]*?\n\}/)?.[0];
assert.ok(pure);
const sandbox={Blob,atob,Uint8Array};
vm.runInNewContext(pure+'\nthis.photoBlob=photoBlob;',sandbox);
const photo={data_url:'data:image/jpeg;base64,'+Buffer.from('photo bytes').toString('base64')};
const got=sandbox.photoBlob(photo);
assert.equal(got.type,'image/jpeg');assert.equal(got.size,11);
assert.throws(()=>sandbox.photoBlob({data_url:'javascript:alert(1)'}),/Invalid saved photo/);
console.log('Fuel, service and expense receipt folder regression tests passed.');
