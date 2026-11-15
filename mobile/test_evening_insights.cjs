'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const page=fs.readFileSync('mobile/MileSage_Mobile_Auto_Refresh.html','utf8');
const start='/* EVENING_PARITY_BEGIN */',end='/* EVENING_PARITY_END */';
assert(page.includes(start)&&page.includes(end),'mobile insight helpers must exist');
const source=page.split(start)[1].split(end)[0];
const sandbox={esc:x=>String(x??'')};
vm.runInNewContext(source+';this.getMetrics=fuelInsightMetrics;this.makeChart=insightLineChart;',sandbox);
const fillups=[
 {date:'2026-11-01',mileage:1000,gallons:'10',cost_cents:4000,full_tank:true},
 {date:'2026-11-04',mileage:1120,gallons:'5',cost_cents:2000,full_tank:false},
 {date:'2026-11-07',mileage:1200,gallons:'7',cost_cents:3000,full_tank:true}
];
const m=sandbox.getMetrics({fuel_history:fillups});
assert.equal(m.price.length,3);
assert.equal(m.distance.length,2);
assert.equal(m.distance[0].value,120);
assert.equal(m.distance[1].value,80);
assert.equal(m.costPerMile.length,1);
assert.equal(m.costPerMile[0].value,0.25);
assert.equal(m.price[0].value,4);
const chart=sandbox.makeChart(m.distance,'miles',0);
assert(chart.includes('<svg') && chart.includes('Latest: 80 miles'));
assert(sandbox.makeChart([], '$/mile',3).includes('At least two'));
const missing=sandbox.getMetrics({fuel_history:[
 fillups[0],{...fillups[1],cost_cents:null},fillups[2]
]});
assert.equal(missing.costPerMile.length,0,'never invent cost per mile with unknown transaction cost');
const reset=sandbox.getMetrics({fuel_history:[
 fillups[0],{...fillups[1],mileage:null},fillups[2]
]});
assert.equal(reset.costPerMile.length,0,'null odometer breaks full-tank interval');
assert(page.includes("const KEY='milesage-mobile-offline-v1'"),'keep original phone storage key');
assert(page.includes('/* RESTORE_GUARDS_BEGIN */'),'preserve safety checks');
console.log('Mobile evening feature regression tests passed');
