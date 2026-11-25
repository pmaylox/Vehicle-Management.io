'use strict';
const fs=require('node:fs');
const vm=require('node:vm');
const assert=require('node:assert/strict');

const paths=[
 'mobile/MileSage_Mobile_Auto_Refresh.html',
 'mobile/MileSage_Alpha_1_3_2_VIN_Lookup.html'
];
const contents=paths.map(p=>fs.readFileSync(p,'utf8'));
assert.equal(contents[0],contents[1],'Both distributed mobile builds must match');
for(const html of contents){
 assert.match(html,/id="addVinButton"/);
 assert.match(html,/id="vinLookupForm"/);
 assert.match(html,/id="vinConfirmForm"/);
 assert.match(html,/\$\{a\.vin\?/);
 assert.match(html,/\$\('vinLookupForm'\)\.onsubmit=lookUpVIN/);
 assert.match(html,/vin:decodedVIN\.vin/);
 const script=html.split('<script>')[1].split('</script>')[0];
 new vm.Script(script);
 const pure=script.split('/* VIN_LOOKUP_BEGIN */')[1]?.split('/* VIN_LOOKUP_END */')[0];
 assert.ok(pure,'VIN functions must be exposed for isolated tests');
 const context=vm.createContext({});
 vm.runInContext(pure,context);
 assert.equal(context.normalizeVIN('1hgcm82633a004352'),'1HGCM82633A004352');
 assert.equal(context.normalizeVIN('1HGCM-82633 A004352'),'1HGCM82633A004352');
 assert.throws(()=>context.normalizeVIN('123'),/17/);
 assert.throws(()=>context.normalizeVIN('1HGCM82633A00I352'),/17/);
 assert.equal(context.vinAlreadyExists([{vin:'1hgcm82633a004352'}],'1HGCM82633A004352'),true);
 assert.equal(context.vinAlreadyExists([{name:'Toyota Tacoma',year:2026}], '1HGCM82633A004352'),false);
 const decoded=context.parseVINDecode({Results:[{ErrorCode:'0',ModelYear:'2026',Make:'TOYOTA',Model:'Tacoma',Trim:'SR5'}]});
 assert.equal(decoded.year,2026);
 assert.equal(decoded.make,'TOYOTA');
 assert.equal(decoded.model,'Tacoma');
 assert.equal(decoded.trim,'SR5');
 assert.throws(()=>context.parseVINDecode({Results:[{ErrorCode:'1',ErrorText:'Invalid check digit',ModelYear:'2026',Make:'TOYOTA',Model:'Tacoma'}]}),/could not verify/);
 assert.throws(()=>context.parseVINDecode({Results:[{ErrorCode:'0',ModelYear:'',Make:'TOYOTA',Model:'Tacoma'}]}),/complete/);
 assert.throws(()=>context.parseVINDecode({Results:[]}),/no vehicle/);
 const normalizeFn=script.slice(script.indexOf('function normalize(data)'),script.indexOf('function save()'));
 vm.runInContext(fs.readFileSync('mobile/car_history_feature.js','utf8'),context);
 vm.runInContext(normalizeFn,context);
 const old={name:'Toyota Tacoma — Tester',year:2026,mileage:5000,service_history:[{date:'2026-11-14',mileage:5000,description:'Test'}]};
 const actual={name:'Toyota Tacoma',vin:'1HGCM82633A004352',year:2026,mileage:6000};
 const result=context.normalize([old,actual]);
 assert.equal(result.length,2,'Test and VIN vehicles must remain separate');
 assert.equal(result[0].service_history.length,1,'Existing test history must survive normalization');
 assert.equal(result[1].vin,actual.vin,'VIN must survive normalization and JSON backups');
 const identity=script.match(/function vehicleID\(a\)\{[^\n]+\}/)?.[0];
 assert.ok(identity,'Vehicle identity helper missing');
 vm.runInContext(identity,context);
 assert.notEqual(context.vehicleID(result[0]),context.vehicleID(result[1]));
}
console.log('PASS: both VIN builds, VIN validation, NHTSA parser, duplicates, garage data preservation');
