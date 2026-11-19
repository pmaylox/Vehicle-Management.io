// Run: node mobile/test_car_history.cjs
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const html = fs.readFileSync('mobile/MileSage_Mobile_Auto_Refresh.html', 'utf8');
const versioned = fs.readFileSync('mobile/MileSage_Alpha_1_3_3_Car_History.html', 'utf8');
const source = fs.readFileSync('mobile/car_history_feature.js', 'utf8').trim();
const section = text => {
  const begin = text.indexOf('/* CAR_HISTORY_BEGIN */');
  const end = text.indexOf('/* CAR_HISTORY_END */', begin);
  assert.ok(begin >= 0 && end > begin, 'embedded source markers must exist');
  return text.slice(begin, end + '/* CAR_HISTORY_END */'.length).trim();
};
assert.equal(section(html), source, 'mobile entrypoint must match shared source');
assert.equal(section(versioned), source, 'versioned preview must match shared source');
assert.ok(html.includes('data-tab="carHistory"'), 'independent bottom tab exists');
assert.ok(html.includes('id="carHistoryBody"'), 'independent Car History view exists');
assert.ok(html.includes('car_history:normalizeCarHistory(x.car_history)'), 'history survives load');
assert.ok(html.includes('renderCarHistory();renderHome();updateBanner()'), 'history renders in app');
assert.ok(html.includes('Car History events would be lost'), 'restore warns on lost history');
assert.ok(html.includes('item.car_history=oldHistory;'), 'backup recovery preserves history');
assert.ok(html.includes('id="quickHistory"'), 'home review reminder shortcut exists');

let saved = null, notice = null, alertText = null;
const vehicleA = {name:'Toyota Tacoma',mileage:5555,service_history:[],car_history:null};
const vehicleB = {name:'Ford Explorer',mileage:12650,service_history:[],car_history:null};
const context = {
  vehicles:[vehicleA,vehicleB],current:0, KEY:'test-history',
  localDate:()=> '2026-11-19',
  localStorage:{setItem(k,v){saved=v;}},
  renderCarHistory(){},updateBanner(){},message(t){notice=t;},
  alert(t){alertText=t;},
};
vm.createContext(context);
vm.runInContext(source,context);
const get = expression => vm.runInContext(expression,context);
assert.equal(get('nextHistoryReview("2024-02-29")'),'2025-02-28');
assert.equal(get('nextHistoryReview("2025-11-19")'),'2026-11-19');
assert.equal(get('nextHistoryReview("bogus")'),null);
assert.equal(get('carHistoryDate("2026-02-30")'),false);
assert.equal(get('carHistoryDue(vehicles[0])'),true);
assert.equal(get('normalizeCarHistory({events:[{date:"2026-01-01",description:"Recall",mileage:8000},{date:"bad"}]}).events.length'),1);
assert.equal(get('normalizeCarHistory({events:[{date:"2026-01-01",mileage:-5}]}).events[0].mileage'),null);

const worked = get('saveCarHistory(vehicles[0],{last_review_date:"2026-11-19",review_source:"CARFAX Car Care",review_notes:"Reviewed",events:[{date:"2026-10-01",category:"Odometer",description:"Reported",source:"CARFAX Car Care",mileage:8000}]}, "saved")');
assert.equal(worked,true);
assert.ok(notice.includes('saved'));
const data = JSON.parse(saved);
assert.equal(data.vehicles[0].car_history.events.length,1);
assert.equal(data.vehicles[0].mileage,5555,'reported mileage never changes live odometer');
assert.equal(data.vehicles[0].service_history.length,0,'no service log merging');
assert.equal(data.vehicles[1].car_history,null,'other vehicle is unchanged');
assert.equal(get('carHistoryDue(vehicles[0])'),false);

context.localStorage.setItem=()=>{throw Error('out of storage');};
const before = JSON.stringify(context.vehicles);
assert.equal(get('saveCarHistory(vehicles[0],{last_review_date:"2026-11-18",events:[]},"fail")'),false);
assert.equal(JSON.stringify(context.vehicles),before,'storage failure rolls back all changes');
assert.ok(alertText.includes('Could not save'));
console.log('Car History mobile checks passed.');
