'use strict';
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const path = 'mobile/MileSage_Alpha_1_3_2_VIN_Lookup.html';
const html = fs.readFileSync(path,'utf8');
const mirror = fs.readFileSync('mobile/MileSage_Mobile_Auto_Refresh.html','utf8');
const java = fs.readFileSync('android/app/src/main/java/io/reddirtcode/milesage/MainActivity.java','utf8');
const gradle = fs.readFileSync('android/app/build.gradle','utf8');
assert.equal(html,mirror,'Mobile HTML copies must stay identical.');
for(const phrase of [
 "window.MileSageAndroid.chooseFuelReceiptPhoto()",
 "fuelScanOwner=a;",
 "applyFuelScanV2(data.text,owner,'Fuel document scan')",
 "Fuel entry NOT saved:",
 "details WITHOUT a receipt photo?",
])assert.ok(html.includes(phrase),'Missing updated gallery or save behavior: '+phrase);
for(const phrase of [
 "FUEL_GALLERY_PHOTO_CODE = 224",
 "Intent.ACTION_OPEN_DOCUMENT",
 'picker.setType("image/*")',
 "InputImage.fromFilePath(this, selected)",
 "fuelScanResult(found.getText(), fuelScanPreview(selected), null)",
 "@JavascriptInterface public void chooseFuelReceiptPhoto()",
])assert.ok(java.includes(phrase),'Missing Android gallery OCR: '+phrase);
assert.match(gradle,/versionCode 151/);
assert.match(gradle,/applicationId 'io\.reddirtcode\.milesage\.alpha1410fueltest'/);
const start=html.indexOf('async function storeReceipt(vehicle,kind,record,mutate){');
const end=html.indexOf('\nfunction renderAll(){',start);
assert.ok(start>=0&&end>start,'Cannot isolate the record-save function');
const isolated=html.slice(start,end);
new vm.Script(isolated);

async function scenario({photo=false,photoPrepError=false,photoStorageError=false,allStorageError=false,approve=true}={}){
 const vehicle={year:2026,name:'Tacoma',mileage:1000,fuel_history:[]};
 const record={date:'2026-11-24',mileage:1000,gallons:'10.882',cost_cents:3916,full_tank:true};
 const events=[];
 let saved='',attempts=0;
 const context={
  receiptFiles:{fuel:photo?{name:'selected.jpg'}:null},
  photoData:async()=>{
   if(photoPrepError)throw Error('Image conversion failed');
   return 'data:image/jpeg;base64,QQ==';
  },
  v:()=>vehicle,
  vehicles:[vehicle],
  current:0,
  KEY:'milesage-storage',
  localStorage:{setItem:(key,data)=>{
   attempts++;
   if(allStorageError||(photoStorageError&&data.includes('"receipt_photo"')))
    throw Error('QuotaExceededError');
   saved=data;
  }},
  photoDir:null,
  updateBanner:()=>{},
  renderAll:()=>{},
  message:m=>events.push(m),
  alert:m=>events.push(m),
  confirm:m=>{events.push(m);return approve;},
  Date,Math,Number,String,JSON,Object,
 };
 vm.createContext(context);
 vm.runInContext(isolated,context);
 let error=null;
 try{
  await context.storeReceipt(vehicle,'fuel',record,()=>vehicle.fuel_history.push(record));
 }catch(e){error=e;}
 return {vehicle,record,saved,attempts,events,error};
}
(async()=>{
 let r=await scenario();
 assert.equal(r.error,null);
 assert.equal(r.vehicle.fuel_history.length,1,'Plain manual entry must save');
 assert.ok(r.saved.includes('"gallons":"10.882"'));
 r=await scenario({photo:true,photoStorageError:true});
 assert.equal(r.error,null,'Photo quota failure should offer a safe save without photo');
 assert.equal(r.vehicle.fuel_history.length,1);
 assert.ok(!r.vehicle.fuel_history[0].receipt_photo);
 assert.ok(r.events.some(x=>x.includes('WITHOUT a receipt photo')));
 r=await scenario({photo:true,photoPrepError:true});
 assert.equal(r.error,null);
 assert.equal(r.vehicle.fuel_history.length,1,'Unreadable photo must not block approved manual entry');
 r=await scenario({photo:true,photoStorageError:true,approve:false});
 assert.ok(r.error&&r.error.message.includes('NOT saved'));
 assert.equal(r.vehicle.fuel_history.length,0,'Declined photo removal must roll back entry');
 r=await scenario({allStorageError:true});
 assert.ok(r.error);
 assert.equal(r.vehicle.fuel_history.length,0,'Full storage failure must not produce phantom records');
 console.log('PASS: native gallery OCR connected and fuel records save/rollback safely.');
})().catch(error=>{console.error(error);process.exitCode=1;});
