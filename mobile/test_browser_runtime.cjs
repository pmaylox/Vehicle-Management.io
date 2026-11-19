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
    // Four-step tire wizard; driver front MUST occupy diagram's upper-left wheel.
    await page.locator('[data-tab="service"]').click();
    assert.ok((await page.locator('#tirePrompt').innerText()).includes('Driver front (front left)'));
    const tireSVG=page.locator('#tireDiagram svg');
    assert.ok((await tireSVG.getAttribute('aria-label')).includes('driver front at upper left'));
    const beforeTires=JSON.parse(await page.evaluate(()=>localStorage.getItem('milesage-mobile-offline-v1')))
      .vehicles[0].tire_pressure_history.length;
    await page.locator('#tireMeasured').fill('35');
    await page.locator('#tireNext').click();
    assert.ok((await page.locator('#tirePrompt').innerText()).includes('Passenger front (front right)'));
    assert.ok((await tireSVG.locator('g[aria-label^="Driver front"]').getAttribute('aria-label')).includes('35 PSI'));
    await page.locator('#tireBack').click();
    assert.equal(await page.locator('#tireMeasured').inputValue(),'35','Previous step must retain entered PSI');
    await page.locator('#tireNext').click();
    await page.locator('#tireMeasured').fill('36');
    await page.locator('#tireNext').click();
    assert.ok((await page.locator('#tirePrompt').innerText()).includes('Driver rear (rear left)'));
    await page.locator('#tireMeasured').fill('34');
    await page.locator('#tireNext').click();
    assert.ok((await page.locator('#tirePrompt').innerText()).includes('Passenger rear (rear right)'));
    assert.equal(await page.locator('#tireFinish').isVisible(),true);
    assert.equal(JSON.parse(await page.evaluate(()=>localStorage.getItem('milesage-mobile-offline-v1')))
      .vehicles[0].tire_pressure_history.length,beforeTires,'Wizard must not save before final confirmation');
    await page.locator('#tireMeasured').fill('35.5');
    await page.locator('#tireFinish').click();
    await page.waitForFunction(()=>JSON.parse(localStorage.getItem('milesage-mobile-offline-v1'))
      .vehicles[0].tire_pressure_history.length===1);
    const tires=JSON.parse(await page.evaluate(()=>localStorage.getItem('milesage-mobile-offline-v1'))).vehicles[0];
    assert.equal(tires.tire_pressures.driver_front,35);
    assert.equal(tires.tire_pressures.passenger_front,36);
    assert.equal(tires.tire_pressures.driver_rear,34);
    assert.equal(tires.tire_pressures.passenger_rear,35.5);

    // Simulate the native Android ML Kit bridge; no CDN/network is available.
    // The camera/gallery photo should reach native OCR and populate Fuel.
    await page.evaluate(()=>{
      window.MileSageAndroid={recognizeReceipt:(id,base64)=>{
        if(!/^[a-zA-Z0-9+/=]+$/.test(base64))throw Error('Expected JPEG base64');
        window.milesageReceiptOcrComplete({
          id,text:'ALLSUPS\nDATE 10/14/2026\nGALLONS 10.882\nPRICE/G 3.599\nFUEL SALE $39.16'
        });
      }};
    });
    await page.locator('[data-tab="fuel"]').click();
    await page.locator('#fuelGalleryInput').setInputFiles({
      name:'fuel-pump-test.png',mimeType:'image/png',buffer:png
    });
    await page.waitForFunction(()=>
      document.querySelector('#fuelGallons')?.value==='10.882' &&
      document.querySelector('#fuelCost')?.value==='39.16');
    assert.equal(await page.locator('#fuelDate').inputValue(),'2026-10-14');
    assert.equal(await page.locator('#fullTank').isChecked(),false,
      'OCR must never assume the tank was filled completely');
    assert.ok((await page.locator('#fuelReceiptProgress').innerText()).includes('Recognized:'));
    assert.equal(await page.locator('#fuelPhotoPreview').isVisible(),true);
    assert.ok((await page.locator('#fuelReceiptOcrText').textContent()).includes('GALLONS 10.882'),
      'OCR text should be present even when the review details are collapsed');
    // No entry is saved merely by scanning; the user must review and save.
    assert.equal(JSON.parse(await page.evaluate(()=>localStorage.getItem('milesage-mobile-offline-v1')))
      .vehicles[0].fuel_history.length,3);


    // New native document-scan callback: cropped JPEG and OCR text arrive as one
    // reviewed draft, with no automatic fuel-history write.
    await page.evaluate(()=>{
      window.MileSageAndroid.scanFuelReceipt=()=>{
        const canvas=document.createElement('canvas');
        canvas.width=16; canvas.height=16;
        const context=canvas.getContext('2d'); context.fillStyle='#ffffff';
        context.fillRect(0,0,16,16);
        window.milesageFuelScanComplete({
          text:'ALLSUPS\nDATE 10/14/2026\nPRODUCT UNL 10.882\nGALL0NS $3.599\nFUEL 5ALE $39.16',
          image:canvas.toDataURL('image/jpeg',0.85)
        });
      };
    });
    await page.locator('[data-tab="home"]').click();
    await page.locator('[data-tab="fuel"]').click();
    assert.equal(await page.evaluate(()=>typeof window.MileSageAndroid.scanFuelReceipt),'function');
    await page.locator('#fuelCameraButton').click();
    await page.waitForFunction(()=>
      document.querySelector('#fuelGallons')?.value==='10.882' &&
      document.querySelector('#fuelCost')?.value==='39.16' &&
      document.querySelector('#fuelPhotoPreview')?.hidden===false);
    assert.ok((await page.locator('#fuelReceiptProgress').innerText()).includes('Verified calculation'));
    assert.equal(JSON.parse(await page.evaluate(()=>localStorage.getItem('milesage-mobile-offline-v1')))
      .vehicles[0].fuel_history.length,3,'native scan must not save until user confirms');

    // End-to-end expense receipt attachment: use a small camera/gallery image,
    // save the expense, check persisted compressed JPEG and full JSON backup.
    await page.locator('[data-tab="expenses"]').click();
    assert.equal(await page.locator('#expenseCameraButton').isVisible(),true);
    assert.equal(await page.locator('#expenseGalleryButton').isVisible(),true);
    await page.locator('#expenseGalleryInput').setInputFiles({name:'parking.png',mimeType:'image/png',buffer:png});
    assert.equal(await page.locator('#expensePhotoPreview').isVisible(),true);
    // The async native OCR callback may still be filling the form. Wait until
    // it settles before submitting, as a real user would review the result.
    await page.waitForFunction(()=>{
      const status=document.querySelector('#expenseReceiptProgress')?.textContent||'';
      const gallery=document.querySelector('#expenseGalleryButton');
      return gallery&&!gallery.disabled&&
        (/Suggested:|Automatic text reading unavailable/.test(status));
    },null,{timeout:15000});
    await page.locator('#extraDesc').fill('Parking receipt — TEST');
    await page.locator('#extraCost').fill('11.20');
    await page.locator('#saveOtherExpense').click();
    try{
      await page.waitForFunction(()=>{
        const a=JSON.parse(localStorage.getItem('milesage-mobile-offline-v1')).vehicles[0];
        return a.mobile_expenses?.length===1&&!!a.mobile_expenses[0].receipt_photo?.data_url;
      },null,{timeout:15000});
    }catch(error){
      const detail=await page.evaluate(()=>{
        const a=JSON.parse(localStorage.getItem('milesage-mobile-offline-v1')).vehicles[0];
        return {expenseCount:a.mobile_expenses?.length,
          hasPhoto:!!a.mobile_expenses?.[0]?.receipt_photo?.data_url,
          progress:document.querySelector('#expenseReceiptProgress')?.textContent,
          description:document.querySelector('#extraDesc')?.value,
          date:document.querySelector('#extraDate')?.value,
          cost:document.querySelector('#extraCost')?.value,
          formValid:document.querySelector('#extraForm')?.checkValidity()};
      });
      throw Error('Expense photo save did not persist for '+filename+': '+JSON.stringify(detail)+'; '+error.message);
    }
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
