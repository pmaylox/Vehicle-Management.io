// Regression test: mobile Service tab layout and cancel-only behavior.
// Run: node mobile/test_service_cancel_layout.cjs
'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const paths=[
 'mobile/MileSage_Mobile_Auto_Refresh.html',
 'mobile/MileSage_Alpha_1_3_2_VIN_Lookup.html',
 'testing/mobile-audit/verified-apk-index.html'
];
const htmls=paths.map(p=>fs.readFileSync(p,'utf8'));
assert.equal(htmls[0],htmls[1],'Both standalone mobile distributions must match');

for(let i=0;i<paths.length;i++){
 const html=htmls[i];
 const script=html.split('<script>')[1]?.split('</script>')[0];
 assert.ok(script,'Missing application script: '+paths[i]);
 new vm.Script(script);
 const start=script.indexOf('function renderService(){');
 const end=script.indexOf('\nfunction wireFuelReceiptPhoto',start);
 assert.ok(start>=0&&end>start,'Missing service renderer: '+paths[i]);
 const render=script.slice(start,end);
 assert.ok(render.includes('el.innerHTML=tirePressureCard(a)+`'),'Tire pressures must appear first');
 assert.ok(render.includes("${recordList(a.service_history,'service')}</div>`+fluidFilterCard(a);"),'Maintenance form/history must appear before Fluids & Filters');
 assert.ok(render.includes('id="cancelServiceEntry" type="button"'),'Cancel must not submit a form');
 assert.ok(render.includes("$('cancelServiceEntry').onclick=()=>cancelServiceEntry(a);"),'Cancel must be wired');
 assert.ok(render.includes('cancel.disabled=true;'),'Cancel must be disabled during save');
 assert.ok(script.includes('if(requestEpoch!==serviceDraftEpoch)return;'),'Cancel must invalidate pending receipt OCR');

 const first=script.indexOf('let serviceDraftEpoch=0;');
 assert.ok(first>=0&&first<start,'Missing isolated cancel handler');
 const code=script.slice(first,start);
 const ids=['serviceForm','serviceDate','serviceOdo','servicePhotoPreview','servicePhotoImage',
  'servicePhotoInfo','receiptProgress','receiptTextReview','receiptOcrText',
  'servicePdfScanStatus','servicePdfPreview','tirePressureForm'];
 const elements=Object.fromEntries(ids.map(id=>[id,{value:'edited',textContent:'edited',
  hidden:false,style:{display:''},removeAttribute(key){this[key]='removed';}}]));
 elements.serviceForm.reset=function(){this.resetCalls=(this.resetCalls||0)+1;};
 elements.tirePressureForm.value='unsaved tire readings';
 const vehicle={mileage:4321,service_history:[{description:'Existing service'}]};
 const messages=[];
 const sandbox={
  $:id=>elements[id],localDate:()=> '2026-11-17',
  clearReceiptPreview:kind=>messages.push('clear:'+kind),
  message:text=>messages.push(text)
 };
 if(i===2){sandbox.servicePdfDraft={id:'unsaved-pdf'};sandbox.servicePdfScanOwner=vehicle;}
 vm.createContext(sandbox);
 vm.runInContext(code+'\nthis.cancelServiceEntry=cancelServiceEntry;',sandbox);
 sandbox.cancelServiceEntry(vehicle);
 assert.equal(elements.serviceForm.resetCalls,1);
 assert.equal(elements.serviceDate.value,'2026-11-17');
 assert.equal(elements.serviceOdo.value,'4321');
 assert.equal(elements.servicePhotoPreview.hidden,true);
 assert.equal(elements.receiptProgress.textContent,'No receipt scanned yet.');
 assert.equal(elements.tirePressureForm.value,'unsaved tire readings','Cancel must not erase tire edits');
 assert.equal(vehicle.service_history.length,1,'Cancel must not change saved history');
 assert.ok(messages.includes('clear:service'));
 if(i===2){
  assert.equal(sandbox.servicePdfDraft,null,'Cancel must clear a pending PDF');
  assert.equal(sandbox.servicePdfScanOwner,null);
  assert.equal(elements.servicePdfPreview.hidden,true);
 }
}
console.log('PASS: Service entry ordering, Cancel controls, pending OCR/PDF discard, no service save or tire-pressure loss');
