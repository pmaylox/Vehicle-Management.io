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
    // Saved backups are browseable after an import and can be chosen repeatedly.
    await page.locator('#dataButton').click();
    await page.locator('#undoImport').click();
    assert.equal(await page.locator('#savedBackupLibrary').isVisible(),true);
    assert.ok((await page.locator('[data-restore-snapshot]').count())>0,
      'Safe imports must create a visible local recovery snapshot');
    const repeatBackup={vehicles:[vehicle],current:0};
    for(let n=0;n<2;n++){
      await page.locator('#browseSavedJson').click();
      await page.locator('#jsonFile').setInputFiles({
        name:'same-full-mobile-backup.json',mimeType:'application/json',
        buffer:Buffer.from(JSON.stringify(repeatBackup))
      });
      await page.waitForFunction(()=>{
        const status=document.querySelector('#jsonImportStatus')?.textContent||'';
        return status.includes('Backup imported successfully') || status.includes('Import not applied');
      });
      // Import safely returns Home; re-open the backup panel to select
      // the same downloaded file again, as a user would do on Samsung.
      if(n===0)await page.locator('#dataButton').click();
      assert.equal(await page.locator('#jsonImportStatus').innerText(),'Backup imported successfully.',
        'Reimporting the same downloaded JSON should not be consumed after first use');
    }
    await page.locator('#dataButton').click();
    assert.ok((await page.locator('[data-restore-snapshot]').count())>0,
      'Recovery snapshots should remain listed after restores');

    for(const tab of ['home','service','fuel','expenses','graphs']){
     await page.locator('[data-tab="'+tab+'"]').click();
     assert.equal(await page.locator('#'+tab).isVisible(),true,tab+' must open');
     const visible=await page.locator('body').innerText();
     assert.ok(!visible.includes('${')&&!visible.includes('function render'),tab+' leaked application code');
     assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),tab+' overflows phone width');
    }
    const navDebug=await page.evaluate(()=>{
      const button=document.querySelector('[data-tab="service"]'),
       nav=document.querySelector('.bottom'),label=document.querySelector('label[for="resaleSource"]'),
       r=button.getBoundingClientRect(),n=nav.getBoundingClientRect();
      const hit=document.elementFromPoint(r.left+r.width/2,r.top+r.height/2);
      return {viewport:[innerWidth,innerHeight],scrollY,
        button:[r.x,r.y,r.width,r.height],nav:[n.x,n.y,n.width,n.height],
        hit:hit?.outerHTML.slice(0,200),navComputed:getComputedStyle(nav).cssText,
        navPosition:getComputedStyle(nav).position,navZ:getComputedStyle(nav).zIndex,
        mainZ:getComputedStyle(document.querySelector('main')).zIndex,
        labelRect:label?Object.values(label.getBoundingClientRect().toJSON()):null,
        navParent:nav.parentElement?.tagName};
    });
    console.log('MILESAGE_NAV_DEBUG',JSON.stringify(navDebug));
    // Rebuilt Service scanner: native one-page crop/OCR populates a draft,
    // attaches its photo and does not save or reset maintenance until approved.
    await page.locator('[data-tab="service"]').click();
    await page.evaluate(()=>{
      window.MileSageAndroid={
        scanServiceReceipt:()=>{
          const canvas=document.createElement('canvas');canvas.width=16;canvas.height=16;
          const context=canvas.getContext('2d');context.fillStyle='#fff';context.fillRect(0,0,16,16);
          window.milesageServiceReceiptComplete({
            text:'INVOICE DATE 11/14/2026\nODO 4560\nSynthetic oil change\nTire rotation\nTOTAL PAID $127.90',
            image:canvas.toDataURL('image/jpeg',0.85)
          });
        }
      };
    });
    await page.locator('#serviceCameraButton').click();
    await page.waitForFunction(()=>
      document.querySelector('#serviceDesc')?.value.includes('Oil change') &&
      document.querySelector('#serviceDate')?.value==='2026-11-14' &&
      document.querySelector('#serviceOdo')?.value==='4560' &&
      document.querySelector('#serviceCost')?.value==='127.90' &&
      document.querySelector('#servicePhotoPreview')?.hidden===false &&
      (document.querySelector('#receiptProgress')?.textContent||'').includes('Suggested from scanned service receipt'),
      null,{timeout:15000});
    assert.equal(await page.locator('#oilReset').isChecked(),true);
    assert.equal(await page.locator('#tireReset').isChecked(),true);
    assert.equal(JSON.parse(await page.evaluate(()=>localStorage.getItem('milesage-mobile-offline-v1')))
      .vehicles[0].service_history.length,1,'OCR must not save service entry');
    await page.locator('#cancelServiceEntry').click();
    assert.equal(await page.locator('#serviceDesc').inputValue(),'');
    assert.equal(await page.locator('#servicePhotoPreview').isVisible(),false);
    assert.equal(JSON.parse(await page.evaluate(()=>localStorage.getItem('milesage-mobile-offline-v1')))
      .vehicles[0].service_history.length,1,'Cancel must retain existing service history');
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
      document.querySelector('#fuelPhotoPreview')?.hidden===false &&
      (document.querySelector('#fuelReceiptProgress')?.textContent||'').includes('Verified calculation'),
      null,{timeout:15000});
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
    // Separate multi-page expense paperwork test: scanned PDF metadata is
    // attached only when Save other expense is pressed, never on scan alone.
    await page.evaluate(()=>{
      window.MileSageAndroid={
        ...window.MileSageAndroid,
        scanExpenseDocument:()=>{
          const id='da1e216e-490b-4f1e-8bbd-50ca81aab111';
          window.milesageExpenseScannerComplete({
            id,pages:3,ocr_pending:true,name:'MileSage-Expense-'+id+'.pdf'
          });
          window.milesageExpenseOCRComplete({
            id,ocr_pages:3,
            text:'--- PAGE 1 ---\nBODY REPAIR ESTIMATE\nINVOICE DATE 11/14/2026\nBUMPER $350.00\n--- PAGE 2 ---\nPARTS TOTAL $350.00\nLABOR TOTAL $650.00\n--- PAGE 3 ---\nTOTAL REPAIR COST $1,500.75'
          });
        },
        openExpenseDocument:id=>{window.__lastOpenedExpensePDF=id;},
        shareExpenseDocument:id=>{window.__lastSharedExpensePDF=id;},
        saveExpenseDocument:id=>{window.__lastExportedExpensePDF=id;}
      };
    });
    await page.locator('#scanExpensePdf').click();
    assert.equal(await page.locator('#expensePdfPreview').isVisible(),true);
    assert.equal(await page.locator('#expensePdfActions').isVisible(),true);
    assert.equal(await page.locator('#expensePdfTextReview').isVisible(),true);
    assert.equal(await page.locator('#extraDate').inputValue(),'2026-11-14');
    assert.equal(await page.locator('#extraCost').inputValue(),'1500.75');
    assert.equal(await page.locator('#extraDesc').inputValue(),'Body repair estimate');
    await page.locator('#viewExpensePdfDraft').click();
    await page.locator('#saveExpensePdfDraft').click();
    await page.locator('#shareExpensePdfDraft').click();
    const draftActions=await page.evaluate(()=>({
      viewed:window.__lastOpenedExpensePDF,
      exported:window.__lastExportedExpensePDF,
      shared:window.__lastSharedExpensePDF
    }));
    assert.equal(draftActions.viewed,'da1e216e-490b-4f1e-8bbd-50ca81aab111');
    assert.equal(draftActions.exported,draftActions.viewed);
    assert.equal(draftActions.shared,draftActions.viewed);
    assert.equal(JSON.parse(await page.evaluate(()=>localStorage.getItem('milesage-mobile-offline-v1')))
      .vehicles[0].mobile_expenses.length,1,'Scanning alone must not save a new expense');
    await page.locator('#clearExpensePdf').click();
    assert.equal(await page.locator('#expensePdfPreview').isVisible(),false);
    await page.locator('#scanExpensePdf').click();
    await page.locator('#extraDesc').fill('Collision body repair estimate — TEST');
    await page.locator('#extraCost').fill('1500.75');
    await page.locator('#saveOtherExpense').click();
    await page.waitForFunction(()=>{
      const expenses=JSON.parse(localStorage.getItem('milesage-mobile-offline-v1'))
        .vehicles[0].mobile_expenses;
      return expenses.length===2&&expenses[1]?.expense_document?.pages===3;
    },null,{timeout:15000});
    assert.equal(await page.locator('[data-expense-pdf="1"]').count(),1);
    assert.equal(await page.locator('[data-expense-pdf-share="1"]').count(),1);
    assert.equal(await page.locator('[data-expense-pdf-save="1"]').count(),1);
    await page.locator('[data-expense-pdf="1"]').click();
    await page.locator('[data-expense-pdf-share="1"]').click();
    await page.locator('[data-expense-pdf-save="1"]').click();
    const routed=await page.evaluate(()=>({
      opened:window.__lastOpenedExpensePDF,shared:window.__lastSharedExpensePDF
    }));
    assert.equal(routed.opened,'da1e216e-490b-4f1e-8bbd-50ca81aab111');
    assert.equal(routed.shared,routed.opened);
    const expensePDF=JSON.parse(await page.evaluate(()=>localStorage.getItem('milesage-mobile-offline-v1')))
      .vehicles[0].mobile_expenses[1].expense_document;
    assert.equal(expensePDF.pages,3);
    assert.ok(!('data_url' in expensePDF),'PDF bytes must not be embedded in JSON data');
    await page.locator('#dataButton').click();
    const expenseBackupDownload=page.waitForEvent('download');
    await page.locator('#exportFull').click();
    const expensePDFBackup=JSON.parse(fs.readFileSync(await (await expenseBackupDownload).path(),'utf8'));
    assert.equal(expensePDFBackup.vehicles[0].mobile_expenses[1].expense_document.id,
      expensePDF.id,'PDF reference must survive backup');
    assert.equal(expensePDFBackup.vehicles[0].mobile_expenses[0].receipt_photo.data_url,
      expenseSaved.mobile_expenses[0].receipt_photo.data_url,
      'Multi-page PDF work must preserve earlier expense photo');

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
    // Graphs: manually entered KBB quote tracks mileage but never fabricates new prices.
    await page.locator('[data-tab="graphs"]').click();
    assert.ok(await page.locator('#resaleForm').isVisible());
    await page.locator('#resaleTrade').fill('32000.00');
    await page.locator('#resalePrivate').fill('35000.00');
    await page.locator('#resaleNotes').fill('Sample quote, not a live KBB estimate');
    await page.locator('#resaleForm button[type="submit"]').click();
    const saleSaved=JSON.parse(await page.evaluate(()=>localStorage.getItem('milesage-mobile-offline-v1')));
    assert.equal(saleSaved.vehicles[0].resale_history.length,1);
    assert.equal(saleSaved.vehicles[0].resale_history[0].trade_in_cents,3200000);
    assert.equal(saleSaved.vehicles[0].resale_history[0].private_party_cents,3500000);
    assert.ok((await page.locator('#graphsBody').innerText()).includes('Valuation history (1)'));
    await page.evaluate(()=>{
      window.MileSageAndroid={...window.MileSageAndroid,
        openResaleValuation:()=>{window.__kbbOpened=true;},
        shareTesterFeedback:text=>{window.__feedbackShared=text;}
      };
    });
    await page.locator('#lookupKBB').click();
    assert.equal(await page.evaluate(()=>window.__kbbOpened),true);

    // Tester #2 feedback: saved locally and shared only after a tester clicks.
    await page.locator('#feedbackShortcut').click();
    assert.ok(await page.locator('#feedbackForm').isVisible());
    await page.locator('#feedbackTitle').fill('Odometer button test');
    await page.locator('#feedbackDetails').fill('The odometer entry could be clearer.');
    await page.locator('#feedbackSteps').fill('Home > odometer > change number.');
    await page.locator('#saveFeedbackOnly').click();
    assert.equal(await page.locator('[data-feedback-share]').count(),1);
    assert.equal(await page.evaluate(()=>window.__feedbackShared||null),null,
      'Feedback must not be sent automatically');
    const storedReports=JSON.parse(await page.evaluate(()=>
      localStorage.getItem('milesage-alpha145-tester-feedback-v1')));
    assert.equal(storedReports.length,1);
    await page.locator('[data-feedback-share]').click();
    const sharedReport=await page.evaluate(()=>window.__feedbackShared);
    assert.ok(sharedReport.includes('Odometer button test'));
    assert.ok(sharedReport.includes('MileSage Alpha'));
    assert.ok(!sharedReport.includes('1HGCM82633A004352'),'Must not attach VIN automatically');
    await page.reload();
    await page.locator('.vehicle-photo').waitFor();
    await page.locator('[data-tab="graphs"]').click();
    assert.equal(await page.locator('[data-resale-delete]').count(),1,
      'Valuation must persist after restart');
    await page.locator('#feedbackShortcut').click();
    assert.equal(await page.locator('[data-feedback-share]').count(),1,
      'Feedback history must persist after restart');

    await page.locator('.vehicle-photo').waitFor();
    assert.deepEqual(errors,[],'Uncaught browser errors');
    console.log('PASS: browser startup, full expense-photo backup/restore, all tabs, vehicle photo and invalid-import preservation:',filename);
   }finally{await context.close();}
  }
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
