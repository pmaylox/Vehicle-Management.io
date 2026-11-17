'use strict';
// Regression tests for safe +, -, and = odometer updates.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const htmlFile = path.join(__dirname, 'MileSage_Mobile_Auto_Refresh.html');
const html = fs.readFileSync(htmlFile, 'utf8');
const fn = html.match(/function odometerNext\(current,operator,amount\)\{[\s\S]*?\r?\n\}\r?\n(?=function mileageForm)/);
assert.ok(fn, 'Pure +, -, = odometer calculator must exist');
const sandbox = {};
vm.runInNewContext(fn[0]+'\nthis.compute=odometerNext;', sandbox);
const next = sandbox.compute;
assert.equal(next(6881,'+',20),6901);
assert.equal(next(6881,'-',20),6861);
assert.equal(next(6881,'=',6555),6555);
assert.equal(next(6881,'=',0),0, 'test vehicle can be corrected to zero');
assert.equal(next(0,'+',20),20);
for(const args of [[0,'-',1],[6881,'-',6882],[6881,'=',-1],[6881,'+',NaN],[6881,'%',20],[6881,'+',1.5],[Number.MAX_SAFE_INTEGER,'+',1]]){
 assert.throws(()=>next(...args), /must be|Enter a whole|Select|result/, 'Reject negative, invalid, or unsafe mileage');
}
for(const op of ['+','-','='])assert.ok(html.includes('data-odometer-op="'+op+'"'), 'Missing '+op+' button');
assert.ok(html.includes('if(!confirm(warning))return;'), 'Mileage decreases require explicit confirmation');
assert.ok(html.includes('a.mobile_mileage_log.push'), 'Corrections must be logged');
assert.ok(html.includes('a.mileage=next;save();renderAll()'), 'Only the selected vehicle mileage should be changed');
assert.ok(html.includes('This changes only this vehicle'), 'Correction warning must explain vehicle scope');
assert.ok(html.includes("const KEY='milesage-mobile-offline-v1'"), 'Do not change mobile storage key');
console.log('Odometer + / - / = tests passed');
