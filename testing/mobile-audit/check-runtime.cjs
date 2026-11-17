const {chromium}=require(process.env.MILESAGE_PLAYWRIGHT_MODULE);
const fs=require('node:fs'),path=require('node:path'),{pathToFileURL}=require('node:url');
const files=['installed-apk-index.html','verified-apk-index.html'];
const data=JSON.parse(fs.readFileSync(path.resolve(__dirname,'../../vehicles.json'),'utf8'));
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
 for(const file of files){
  const context=await browser.newContext({viewport:{width:390,height:844},isMobile:true});
  const page=await context.newPage(),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.route('https://**/*',route=>route.abort());
  await page.goto(pathToFileURL(path.join(__dirname,file)).href);
  await page.evaluate(records=>localStorage.setItem('milesage-mobile-offline-v1',JSON.stringify({vehicles:records,current:0})),data);
  await page.reload();
  const report={file,errors,cards:await page.locator('[data-vehicle]').count(),screens:{}};
  for(const tab of ['home','service','fuel','expenses','graphs']){
   await page.locator('[data-tab="'+tab+'"]').evaluate(button=>button.click());
   const body=await page.locator('body').innerText();
   report.screens[tab]={rawCode:body.includes('${')||body.includes('function render'),overflow:await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)};
  }
  await page.screenshot({path:path.join(__dirname,file.replace('.html','.png')),fullPage:true});
  console.log(JSON.stringify(report));
  await context.close();
 }
 await browser.close();
})().catch(error=>{console.error(error);process.exit(1);});
