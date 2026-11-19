'use strict';
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const paths=['mobile/MileSage_Mobile_Auto_Refresh.html','mobile/MileSage_Alpha_1_3_3_Car_History.html'];
assert.equal(fs.readFileSync(paths[0],'utf8'),fs.readFileSync(paths[1],'utf8'));
(async()=>{
 for(const path of paths){
  const html=fs.readFileSync(path,'utf8'),script=html.split('<script>')[1].split('</script>')[0];
  new vm.Script(script);
  const block=script.split('/* VEHICLE_PHOTOS_BEGIN */')[1].split('/* VEHICLE_PHOTOS_END */')[0];
  const elements={};
  const get=id=>elements[id]||(elements[id]={textContent:'',click(){}});
  const first={name:'Tacoma',mileage:4790,service_history:[{description:'keep me'}]},second={name:'Explorer'};
  const photo='data:image/png;base64,aGVsbG8=';
  let drawn=false,saves=0,fail=false;
  const context=vm.createContext({
   vehicles:[first,second],current:0,esc:s=>String(s).replaceAll('"','&quot;'),
   $:get,confirm:()=>true,alert:()=>{},URL:{createObjectURL:()=> 'blob:test',revokeObjectURL:()=>{}},
   Image:class{constructor(){this.naturalWidth=1800;this.naturalHeight=1000;}set src(value){this.onload();}},
   document:{createElement(){return {getContext(){return {drawImage(){drawn=true;}};},toDataURL(type){assert.equal(type,'image/png');return photo;}};}}
  });
  context.v=()=>context.vehicles[context.current];
  context.commitImport=(updated,current)=>{saves++;if(fail)return false;context.vehicles=updated;context.current=current;return true;};
  vm.runInContext(block,context);
  assert.equal(context.safeVehiclePhoto('C:/Users/private/photo.png'),'');
  assert.equal(context.safeVehiclePhoto('javascript:alert(1)'),'');
  assert.equal(context.safeVehiclePhoto('data:image/svg+xml;base64,aGVsbG8='),'');
  assert.equal(context.safeVehiclePhoto('https://example.com/track.png'),'');
  assert.equal(context.safeVehiclePhoto(photo),photo);
  assert.match(context.vehiclePhotoHTML(first),/placeholder/);
  assert.match(context.vehiclePhotoHTML({...first,mobile_photo:photo}),/<img/);
  await assert.rejects(context.prepareVehiclePhoto({type:'text/plain',size:1}));
  await assert.rejects(context.prepareVehiclePhoto({type:'image/png',size:21*1024*1024}));
  assert.equal(await context.prepareVehiclePhoto({type:'image/png',size:100}),photo);
  assert.ok(drawn);
  context.wireVehiclePhotos();
  const event=()=>({target:{files:[{type:'image/png',size:100}],value:'test'}});
  await get('vehiclePhotoFile').onchange(event());
  assert.equal(context.vehicles[0].mobile_photo,photo);
  assert.equal(first.mobile_photo,undefined,'Original record is immutable');
  assert.strictEqual(context.vehicles[0].service_history,first.service_history);
  assert.strictEqual(context.vehicles[1],second,'Other vehicle is unchanged');
  assert.equal(JSON.parse(JSON.stringify(context.vehicles))[0].mobile_photo,photo,'JSON backup retains image');
  const saved=context.vehicles;
  fail=true;await get('vehiclePhotoFile').onchange(event());
  assert.strictEqual(context.vehicles,saved,'Failed storage must preserve records');
  fail=false;
  const pending=get('vehiclePhotoFile').onchange(event());context.current=1;await pending;
  assert.strictEqual(context.vehicles,saved,'Selection changes cannot attach to the wrong vehicle');
  context.current=0;get('removeVehiclePhoto').onclick();
  assert.equal(context.vehicles[0].mobile_photo,'');
  assert.strictEqual(context.vehicles[0].service_history,first.service_history);
  assert.ok(saves>=3);
 }
 console.log('PASS: mobile vehicle photo display, PNG preparation, backup persistence, storage rollback, selection isolation and removal');
})().catch(error=>{console.error(error);process.exitCode=1;});
