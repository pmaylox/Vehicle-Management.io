'use strict';
const fs=require('node:fs');
const vm=require('node:vm');
const assert=require('node:assert/strict');

const paths=[
 'mobile/MileSage_Mobile_Auto_Refresh.html',
 'mobile/MileSage_Alpha_1_3_3_Car_History.html'
];
const files=paths.map(p=>fs.readFileSync(p,'utf8'));
assert.equal(files[0],files[1],'Both distributed mobile builds must stay identical');

for(const html of files){
 for(const id of ['manageVehicle','editVehicle','removeVehicle','editVehicleForm',
   'editVehicleName','editVehicleYear','editVehicleVIN','cancelVehicleEdit']){
  assert.ok(html.includes('id="'+id+'"'),'Missing vehicle management control: '+id);
 }
 assert.ok(html.includes('renderVehicles();renderVehicleControls();'),
  'Selected-vehicle controls must refresh with the garage');
 assert.match(html,/wireVehicleControls\(\);/,'Vehicle management must be wired on startup');
 assert.match(html,/commitImport\(updated,selected,'Vehicle details updated\.'\)/);
 assert.match(html,/commitImport\(remaining,nextIndex,'Vehicle removed\.'\)/);
 assert.match(html,/type REMOVE in capital letters/,
  'Removing a vehicle must require explicit typed confirmation');
 assert.match(html,/Restore previous local snapshot/,
  'Recovery must remain available after a vehicle change');

 const script=html.split('<script>')[1]?.split('</script>')[0];
 assert.ok(script,'Missing mobile application script');
 new vm.Script(script);
 const management=script.split('/* VEHICLE_MANAGEMENT_BEGIN */')[1]?.split('/* VEHICLE_MANAGEMENT_END */')[0];
 const vinFunctions=script.split('/* VIN_LOOKUP_BEGIN */')[1]?.split('/* VIN_LOOKUP_END */')[0];
 const whole=script.slice(script.indexOf('function whole('),script.indexOf('function normalize(data)'));
 assert.ok(management&&vinFunctions&&whole,'Missing isolated validation functions');
 const context=vm.createContext({});
 vm.runInContext(whole+'\n'+vinFunctions+'\n'+management,context);

 const service=[{date:'2026-11-14',mileage:4000,description:'Oil change'}];
 const fuel=[{date:'2026-11-15',mileage:4100,gallons:13}];
 const real={name:'Toyota Tacoma',year:2026,mileage:4605,vin:null,
  service_history:service,fuel_history:fuel,tire_pressures:{driver_front:35}};
 const demo={name:'Toyota Tacoma — Test',year:2026,mileage:0,vin:null,
  service_history:[],fuel_history:[]};
 const explorer={name:'Ford Explorer',year:2025,mileage:32162,vin:'1HGCM82633A004352'};
 const garage=[real,demo,explorer];

 const edited=context.editVehicleDetails(real,'Toyota Tacoma (Real)','2026',
  '2T3WFREV7JW123456',garage,0);
 assert.equal(real.name,'Toyota Tacoma','Original vehicle cannot be modified');
 assert.equal(real.vin,null,'Editing cannot mutate the original VIN');
 assert.equal(edited.name,'Toyota Tacoma (Real)');
 assert.equal(edited.vin,'2T3WFREV7JW123456');
 assert.equal(edited.mileage,4605,'Editing vehicle details must not alter mileage');
 assert.strictEqual(edited.service_history,service,'Service history must be retained');
 assert.strictEqual(edited.fuel_history,fuel,'Fuel history must be retained');
 assert.strictEqual(edited.tire_pressures,real.tire_pressures,'Tire pressures must be retained');
 assert.equal(garage[1].name,'Toyota Tacoma — Test','Test vehicle must remain separate');

 assert.throws(()=>context.editVehicleDetails(real,'  ','2026','',garage,0),/name/);
 assert.throws(()=>context.editVehicleDetails(real,'Tacoma','1800','',garage,0),/1900/);
 assert.throws(()=>context.editVehicleDetails(real,'Tacoma','2026','INVALID',garage,0),/VIN/);
 assert.throws(()=>context.editVehicleDetails(real,'Tacoma','2026',explorer.vin,garage,0),/another vehicle/);

 const remaining=context.removeVehicleAt(garage,1);
 assert.equal(remaining.length,2,'Only the selected vehicle is removed');
 assert.strictEqual(remaining[0],real,'Real Tacoma must remain untouched');
 assert.strictEqual(remaining[1],explorer,'Real Explorer must remain untouched');
 assert.equal(garage.length,3,'Removal helper must not mutate the original array');
 assert.throws(()=>context.removeVehicleAt(garage,99),/valid vehicle/);
}
console.log('PASS: mobile edit/remove controls, metadata validation, VIN duplicates, isolated deletion, record preservation, JS syntax');
