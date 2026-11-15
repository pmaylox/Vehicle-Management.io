// Run: node mobile/test_fuel_receipt_parser.cjs
const fs=require('node:fs');
const vm=require('node:vm');
const assert=require('node:assert/strict');
const html=fs.readFileSync('mobile/MileSage_Mobile_Auto_Refresh.html','utf8');
const svc=html.split('/* RECEIPT_PARSER_BEGIN */')[1]?.split('/* RECEIPT_PARSER_END */')[0];
const fuel=html.split('/* FUEL_RECEIPT_PARSER_BEGIN */')[1]?.split('/* FUEL_RECEIPT_PARSER_END */')[0];
assert.ok(svc&&fuel, 'Both receipt parsers must exist');
const sandbox={Date,Number,String,Array,Object};
vm.runInNewContext(svc+'\n'+fuel,sandbox);
const parse=x=>sandbox.parseFuelReceiptText(x,'2026-11-14');

const first=parse([
 'FUEL RECEIPT',
 'Date: 11/14/2026 12:44',
 'Regular 87',
 'Price/Gal $3.159',
 'Gallons: 12.345',
 'Odometer: 7,135',
 'Total: $39.00',
 'Visa ***2413',
].join('\n'));
assert.equal(first.date,'2026-11-14');
assert.equal(first.mileage,7135);
assert.equal(first.gallons,'12.345');
assert.equal(first.total,'39.00');

const second=parse([
 'STORE RECEIPT','Date: 11/10/2026',
 'UNLEADED 16.218 GAL',
 'PPU 2.999',
 'Sale Total $48.64'
].join('\n'));
assert.equal(second.date,'2026-11-10');
assert.equal(second.gallons,'16.218');
assert.equal(second.total,'48.64');
assert.equal(second.mileage,null, 'odometer must not be invented if absent');

const third=parse('Date 11/16/2026\nPrice/Gallon 3.199\nSubtotal 51.20\nTax 0.00');
assert.equal(third.date,null,'future date should not populate');
assert.equal(third.gallons,null,'price per gallon should not become volume');
assert.equal(third.total,null,'subtotal should not become final total');

const fourth=parse('Fuel Volume: 9.45 US GAL\nGrand Total: $28.35\nDate 2026-11-13');
assert.equal(fourth.gallons,'9.45');
assert.equal(fourth.total,'28.35');
assert.equal(fourth.date,'2026-11-13');

assert.ok(html.includes('capture="environment"'));
assert.ok(html.includes('wireFuelReceiptPhoto(a)'));
assert.ok(html.includes("if(od>a.mileage)throw Error"), 'fuel save must retain odometer safety validation');
assert.ok(html.includes("$('fullTank').checked=false"), 'OCR may not claim a full tank');
assert.ok(html.includes('id="fuelPhotoPreview"'), 'fuel photo must show a temporary preview');
assert.ok(html.includes("showReceiptPreview('fuel',file)"), 'fuel must preview the received photo before OCR starts');
assert.ok(html.includes('Photo preview is shown, but fuel receipt scanning failed:'), 'fuel must report OCR failures without hiding the photo');
console.log('Fuel receipt OCR parsing tests passed');
