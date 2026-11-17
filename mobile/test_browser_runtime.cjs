'use strict';
// Real browser tests: use an isolated garage, never the user's browser profile.
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),{pathToFileURL}=require('node:url');
const {chromium}=require(process.env.MILESAGE_PLAYWRIGHT_MODULE||'playwright');
const png=Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aL1sAAAAASUVORK5CYII=','base64');
const vehicle={name:'Tacoma Runtime TEST',year:2026,mileage:4605,starting_mileage:1000,
 service_interval:5000,last_service_mileage:4200,tire_rotation_interval:5000,
 service_history:[{date:'2026-10-01',mileage:4200,description:'Oil change',cost_cents:7500}],
 fuel_history:[{date:'2026-10-01',mileage:4000,gallons:'12.000',cost_cents:3600,full_tank:true},
 {date:'2026-10-15',mileage:4250,gallons:'11.500',cost_cents:3500,full_tank:true},
 {date:'2026-11-01',mileage:4500,gallons:'12.000',cost_cents:3700,full_tank:true}]};
const files=process.argv.slice(2);
if(!files.length)files.push('mobile/MileSage_Mobile_Auto_Refresh.html','mobile/MileSage_Alpha_1_3_2_VIN_Lookup.html');
(async()=>{
 const browser=await chromium.launch({headless:true,...(process.env.MILESAGE_CHROME?{executablePath:process.env.MILESAGE_CHROME}:{})});
 try{
  for(const filename of files){
   const context=await browser.newContext({viewport:{width:390,height:844},isMobile:true});
   try{
    const page=await context.newPage(),errors=[];
    page.on('pageerror',error=>errors.push(error.message));
    page.on('dialog',dialog=>dialog.accept());
    await page.route('https://**/*',route=>route.abort());
    await page.goto(pathToFileURL(path.resolve(filename)).href,{waitUntil:'domcontentloaded'});
    await page.locator('#dataButton').click();
    await page.locator('#jsonFile').setInputFiles({name:'runtime-backup.json',mimeType:'application/json',
     buffer:Buffer.from(JSON.stringify({vehicles:[vehicle],current:0}))});
    await page.locator('[data-vehicle="0"]').waitFor();
    for(const tab of ['home','service','fuel','expenses','graphs']){
     await page.locator('[data-tab="'+tab+'"]').click();
     assert.equal(await page.locator('#'+tab).isVisible(),true,tab+' must open');
     const visible=await page.locator('body').innerText();
     assert.ok(!visible.includes('${')&&!visible.includes('function render'),tab+' leaked application code');
     assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),tab+' overflows phone width');
    }
    // End-to-end expense receipt attachment: use a small camera/gallery image,
    // save the expense, check persisted compressed JPEG and full JSON backup.
    await page.locator('[data-tab="expenses"]').click();
    assert.equal(await page.locator('#expenseCameraButton').isVisible(),true);
    assert.equal(await page.locator('#expenseGalleryButton').isVisible(),true);
    await page.locator('#expenseGalleryInput').setInputFiles({name:'parking.png',mimeType:'image/png',buffer:png});
    assert.equal(await page.locator('#expensePhotoPreview').isVisible(),true);
    await page.locator('#extraDesc').fill('Parking receipt — TEST');
    await page.locator('#extraCost').fill('11.20');
    await page.locator('#saveOtherExpense').click();
    await page.waitForFunction(()=>{
      const a=JSON.parse(localStorage.getItem('milesage-mobile-offline-v1')).vehicles[0];
      return a.mobile_expenses?.length===1&&!!a.mobile_expenses[0].receipt_photo?.data_url;
    });
    const expenseSaved=JSON.parse(await page.evaluate(()=>localStorage.getItem('milesage-mobile-offline-v1'))).vehicles[0];
    assert.equal(expenseSaved.mobile_expenses[0].description,'Parking receipt — TEST');
    assert.equal(expenseSaved.mobile_expenses[0].cost_cents,1120);
    assert.ok(expenseSaved.mobile_expenses[0].receipt_photo.data_url.startsWith('data:image/jpeg;base64,'));
    assert.equal(await page.locator('[data-photo-download="expense:0"]').count(),1);
    assert.ok((await page.locator('#expensesBody').innerText()).includes('Parking receipt — TEST'));
    await page.locator('#dataButton').click();
    const downloadPromise=page.waitForEvent('download');
    await page.locator('#exportFull').click();
    const receiptBackup=JSON.parse(fs.readFileSync(await (await downloadPromise).path(),'utf8'));
    assert.equal(receiptBackup.format,'MileSage-Mobile-v1');
    assert.equal(receiptBackup.vehicles[0].mobile_expenses[0].receipt_photo.data_url,
      expenseSaved.mobile_expenses[0].receipt_photo.data_url,'Full mobile backup lost expense receipt');
    await page.locator('#jsonFile').setInputFiles({
      name:'expense-backup.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(receiptBackup))
    });
    await page.waitForTimeout(200);
    assert.equal(JSON.parse(await page.evaluate(()=>localStorage.getItem('milesage-mobile-offline-v1')))
      .vehicles[0].mobile_expenses[0].receipt_photo.data_url,
      expenseSaved.mobile_expenses[0].receipt_photo.data_url,'Expense receipt lost on restore');
    await page.locator('[data-tab="expenses"]').click();
    assert.equal(await page.locator('[data-photo-download="expense:0"]').count(),1);
    await page.locator('[data-tab="home"]').click();
    await page.locator('#vehiclePhotoFile').setInputFiles({name:'vehicle.png',mimeType:'image/png',buffer:png});
    await page.locator('.vehicle-photo').waitFor();
    assert.ok(await page.locator('.vehicle-photo').evaluate(image=>image.complete&&image.naturalWidth>0));
    const snapshot=await page.evaluate(()=>localStorage.getItem('milesage-mobile-offline-v1'));
    assert.ok(JSON.parse(snapshot).vehicles[0].mobile_photo.startsWith('data:image/png;base64,'));
    await page.locator('#dataButton').click();
    await page.locator('#jsonFile').setInputFiles({name:'invalid.json',mimeType:'application/json',buffer:Buffer.from('{broken')});
    await page.waitForTimeout(100);
    assert.equal(await page.evaluate(()=>localStorage.getItem('milesage-mobile-offline-v1')),snapshot,'Invalid import changed saved records');
    await page.locator('#jsonFile').setInputFiles({name:'bad-history.json',mimeType:'application/json',
     buffer:Buffer.from(JSON.stringify({vehicles:[{...vehicle,fuel_history:[null]}]}))});
    await page.waitForTimeout(100);
    assert.equal(await page.evaluate(()=>localStorage.getItem('milesage-mobile-offline-v1')),snapshot,'Invalid history changed saved records');
    assert.ok((await page.locator('#jsonImportStatus').innerText()).includes('Import failed'));
    await page.reload();
    await page.locator('.vehicle-photo').waitFor();
    assert.deepEqual(errors,[],'Uncaught browser errors');
    console.log('PASS: browser startup, full expense-photo backup/restore, all tabs, vehicle photo and invalid-import preservation:',filename);
   }finally{await context.close();}
  }
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
