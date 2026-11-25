'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {pathToFileURL}=require('node:url');
const {chromium}=require(process.env.MILESAGE_PLAYWRIGHT_MODULE||'playwright');
(async()=>{
 const browser=await chromium.launch({headless:true,...(process.env.MILESAGE_CHROME?{executablePath:process.env.MILESAGE_CHROME}:{})});
 try{
  for(const width of [360,390,1024]){
   const context=await browser.newContext({viewport:{width,height:900}});
   const page=await context.newPage(),errors=[];
   page.on('pageerror',e=>errors.push(e.message));page.on('dialog',d=>d.accept());
   await page.route('https://**/*',r=>r.abort());
   await page.goto(pathToFileURL(path.resolve('mobile/MileSage_Mobile_Auto_Refresh.html')).href);
   await page.locator('#dataButton').click();
   const garage=[{name:'Interface Tester',year:2026,mileage:5000,last_service_mileage:4500,
    mobile_expenses:[{date:'2026-11-01',cost_cents:100,description:'Parking'}],mobile_mileage_log:[{before:4990,after:5000}]}];
   await page.locator('#jsonFile').setInputFiles({name:'test.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(garage))});
   for(const tab of ['home','service','fuel','expenses','carHistory','graphs']){
    await page.locator(`[data-tab="${tab}"]`).click();
    assert.ok(await page.locator('#'+tab).isVisible());
    assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`${tab} overflows at ${width}`);
    const box=await page.locator(`[data-tab="${tab}"]`).boundingBox();
    assert.ok(box.y+box.height<=900,'Navigation is outside viewport');
   }
   await page.locator('[data-tab="carHistory"]').click();
   await page.locator('#carEventDescription').fill('Reported recall reviewed');
   await page.locator('#carEventMiles').fill('9000');
   await page.locator('#carEventForm button[type="submit"]').click();
   const saved=await page.evaluate(()=>JSON.parse(localStorage.getItem('milesage-mobile-offline-v1')));
   assert.equal(saved.vehicles[0].car_history.events.length,1);
   assert.equal(saved.vehicles[0].mileage,5000,'Reported history changed live odometer');
   await page.locator('#dataButton').click();
   const download=page.waitForEvent('download');await page.locator('#exportPython').click();
   const exported=JSON.parse(fs.readFileSync(await (await download).path(),'utf8'));
   assert.equal(exported[0].mobile_expenses.length,1);
   assert.equal(exported[0].mobile_mileage_log.length,1);
   assert.equal(exported[0].car_history.events.length,1);
   await page.reload();await page.locator('[data-tab="carHistory"]').click();
   assert.ok((await page.locator('#carHistoryBody').innerText()).includes('Reported recall reviewed'));
   assert.deepEqual(errors,[]);
   console.log(`PASS: shared navigation, history persistence, safe odometer and desktop export at ${width}px`);
   await context.close();
  }
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1});
