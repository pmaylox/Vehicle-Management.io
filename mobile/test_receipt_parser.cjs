// Test OCR parsing without sending receipts to any service.
// Run: node mobile/test_receipt_parser.cjs
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const html = fs.readFileSync('mobile/MileSage_Mobile_Auto_Refresh.html','utf8');
const parser = html.split('/* RECEIPT_PARSER_BEGIN */')[1]?.split('/* RECEIPT_PARSER_END */')[0];
assert.ok(parser, 'embedded receipt parser missing');
const context = {Date,Number,String,Array,Object};
vm.runInNewContext(parser,context);

const text = [
 'SERVICE INVOICE',
 'Invoice Number 5531',
 'Service Date: 11/14/2026',
 'Odometer: 6,881',
 'Synthetic Oil Change',
 'Tire Rotation',
 'Cabin Air Filter Replaced',
 'Engine Air Filter Inspected',
 'Subtotal $116.95',
 'Tax $8.00',
 'Invoice Total: $124.95',
].join('\n');
const parsed=context.parseServiceReceiptText(text,'2026-11-14');
assert.equal(parsed.date,'2026-11-14');
assert.equal(parsed.mileage,6881);
assert.equal(parsed.cost,'124.95');
assert.equal(parsed.oil,true);
assert.equal(parsed.tire,true);
assert.equal(parsed.cabin,true);
assert.equal(parsed.engine,false, 'inspection alone must not mark engine air filter replaced');
assert.match(parsed.description,/Oil change/);
assert.match(parsed.description,/Tire rotation/);

const future=context.parseServiceReceiptText('Date: 11/15/2026\nMiles: 13,145\nPaid Amount $76.20','2026-11-14');
assert.equal(future.date,null,'future receipt date must not auto-fill');
assert.equal(future.mileage,13145);
assert.equal(future.cost,'76.20');
const blank=context.parseServiceReceiptText('Welcome back! No data','2026-11-14');
assert.equal(blank.date,null);
assert.equal(blank.mileage,null);
assert.equal(blank.cost,null);
assert.equal(blank.description,null);
assert.ok(html.includes('capture="environment"'), 'mobile photo capture is required');
assert.ok(html.includes('wireServiceReceiptPhoto(a)'), 'receipt camera handlers must be wired');
assert.ok(html.includes("if(od>a.mileage)throw Error"), 'receipt may not silently increase odometer');
assert.ok(html.includes('id="servicePhotoPreview"'), 'service photo must show a temporary preview');
assert.ok(html.includes("showReceiptPreview('service',file)"), 'service must preview the received photo before OCR starts');
assert.ok(html.includes('Photo preview is shown, but receipt scanning failed:'), 'service must report OCR failures without hiding the photo');
console.log('Receipt parsing tests passed.');
