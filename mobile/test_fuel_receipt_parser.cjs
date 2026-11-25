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
assert.equal(fourth.gallons,'9.450');
assert.equal(fourth.total,'28.35');
assert.equal(fourth.date,'2026-11-13');


const actualPump=sandbox.parseFuelReceiptText([
 'ALLSUPS #20483',
 'DATE 11/16/26 4:47',
 'PUMP 02',
 'PRODUCT RU',
 'GALLONS 10.882',
 'PRICE/G 3.599',
 'FUEL SALE $39.16',
 'CREDIT $39.16',
].join('\n'),'2026-11-16');
assert.equal(actualPump.gallons,'10.882','Allsup fuel receipt quantity must autofill');
assert.equal(actualPump.total,'39.16','Fuel sale, not pump price, must become total');
assert.equal(actualPump.date,'2026-11-16');

const wrapped=sandbox.parseFuelReceiptText([
 'GALLONS','10.882','PRICE/GALLON','3.599','FUEL SALE','$39.16'
].join('\n'),'2026-11-16');
assert.equal(wrapped.gallons,'10.882','OCR line-wrapped gallons must autofill');
assert.equal(wrapped.total,'39.16','OCR line-wrapped fuel sale must autofill');

const damaged=sandbox.parseFuelReceiptText([
 'GALL0NS: 10,882', 'FUEL 5ALE 39.16'
].join('\n'),'2026-11-16');
assert.equal(damaged.gallons,'10.882','Common OCR zero/comma substitutions must be recognized');
assert.equal(damaged.total,'39.16','Common OCR 5/sale substitution must be recognized');

const unitPriceOnly=sandbox.parseFuelReceiptText('PRICE/GALLON 3.599\nSUBTOTAL 39.16\nTAX 0.00','2026-11-16');
assert.equal(unitPriceOnly.gallons,null,'Never infer volume from price-per-gallon');
assert.equal(unitPriceOnly.total,null,'Never infer total from subtotal or tax');

assert.equal(sandbox.parseGallonsInput('12.5'),'12.500');
assert.equal(sandbox.parseGallonsInput('10.882'),'10.882');
assert.equal(sandbox.parseGallonsInput('9'),'9.000');
assert.throws(()=>sandbox.parseGallonsInput('10.8825'),/3 decimal places/);
assert.throws(()=>sandbox.parseGallonsInput('0'),/valid US gallon amount/);
assert.ok(html.includes('step="0.001" placeholder="12.500"'));
assert.ok(html.includes("const gal=parseGallonsInput($('fuelGallons').value)"));
assert.ok(html.includes("mileage:od,gallons:gal,cost_cents:cost"));

assert.ok(html.includes('capture="environment"'));
assert.ok(html.includes('wireFuelReceiptPhoto(a)'));
assert.ok(html.includes("const od=whole($('fuelOdo').value,'Odometer',0)"), 'historical receipt odometer may be logged without downgrading current mileage');
assert.ok(html.includes('if(od>a.mileage){a.mobile_mileage_log.push'), 'only higher fuel readings advance vehicle mileage');
assert.ok(html.includes("storeReceipt(a,'fuel'"), 'fuel record and receipt are persisted together');
assert.ok(html.includes("$('fullTank').checked=false"), 'OCR may not claim a full tank');
assert.ok(html.includes('id="fuelPhotoPreview"'), 'fuel photo must show a temporary preview');
assert.ok(html.includes("showReceiptPreview('fuel',file)"), 'fuel must preview the received photo before OCR starts');
assert.ok(html.includes('Photo preview is shown, but fuel receipt scanning failed:'), 'fuel must report OCR failures without hiding the photo');
console.log('Fuel receipt OCR parsing tests passed');


const allsups=parse('ALLSUPS #t 102483\nWELCOME TO\nRU CR #06\nDescription\nUSD$53.34\nSELF @ 3.319/ G');
assert.equal(allsups.total,'53.34');
assert.equal(parse('TOTAL $39.00\nUSD$40.00').total,'39.00');
assert.equal(parse('USD$53.34\nUSD$10.00').total,null);
assert.equal(parse('CREDIT $53.34').total,'53.34');
