// Run: node mobile/test_restore_safety.cjs
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const text = fs.readFileSync('mobile/MileSage_Mobile_Auto_Refresh.html', 'utf8');
const code = text.split('/* RESTORE_GUARDS_BEGIN */')[1]?.split('/* RESTORE_GUARDS_END */')[0];
const historyHelpers = text.split('/* CAR_HISTORY_BEGIN */')[1]?.split('/* CAR_HISTORY_END */')[0];
assert.ok(historyHelpers, 'Car History normalizer must be available to restore tests');
assert.ok(code, 'guard code must be present');
const context = {JSON, Number, String, Object, Array};
vm.runInNewContext(historyHelpers + '\n' + code, context);

const empty = [{name:'Toyota Tacoma', year:2026, mileage:0,
  tire_pressures:{driver_front:null, driver_rear:null},
  service_history:[], fuel_history:[], tire_pressure_history:[]}];
assert.equal(context.isBlankSeed(empty), true);
const recorded = [{name:'Toyota Tacoma', year:2026, mileage:6881,
  tire_pressures:{driver_front:35, driver_rear:null},
  starting_tire_pressures:{driver_front:35, driver_rear:null},
  service_history:[{date:'2026-10-31'}], fuel_history:[],
  tire_pressure_history:[],fluid_check_history:[],air_filter_changes:[],
  mobile_expenses:[],mobile_mileage_log:[],
  fluid_checks:{washer:{last_full_mileage:null},coolant:{last_full_mileage:null}},
  service_interval:10000,tire_rotation_interval:5000}];
assert.equal(context.isBlankSeed(recorded), false);
const issues = context.destructiveDiffs(recorded, empty);
assert.ok(issues.some(s=>s.includes('mileage')));
assert.ok(issues.some(s=>s.includes('pressure')));
assert.ok(issues.some(s=>s.includes('service history')));
const oldBackup = [{...recorded[0], mileage:6400, service_interval:5500,
  tire_rotation_interval:10000,
  tire_pressures:{driver_front:33,driver_rear:35},
  starting_tire_pressures:{driver_front:33,driver_rear:35},
  service_history:[{date:'2026-09-01'}]}];
const recovered=context.mergeRecovery(recorded,oldBackup);
assert.equal(recovered[0].mileage,6881,'newer odometer cannot be downgraded');
assert.equal(recovered[0].tire_pressures.driver_front,35,'existing PSI preserved');
assert.equal(recovered[0].tire_pressures.driver_rear,35,'missing PSI recovered');
assert.equal(recovered[0].service_interval,10000,'configured interval preserved');
assert.equal(recovered[0].tire_rotation_interval,5000,'configured tire interval preserved');
assert.equal(recovered[0].service_history.length,1,'existing service log preserved');
const blankLocal = JSON.parse(JSON.stringify(empty));
blankLocal[0].service_interval=10000;
blankLocal[0].tire_rotation_interval=5000;
blankLocal[0].starting_tire_pressures={driver_front:null,driver_rear:null};
blankLocal[0].fluid_checks={washer:{last_full_mileage:null},coolant:{last_full_mileage:null}};
const recoveredBlank=context.mergeRecovery(blankLocal,oldBackup);
assert.equal(recoveredBlank[0].mileage,6400,'empty odometer recovered');
assert.equal(recoveredBlank[0].service_interval,10000,'service interval preserved during recovery');
assert.equal(recoveredBlank[0].tire_rotation_interval,5000,'rotation interval preserved during recovery');
const autoRefresh=text.split('async function autoRefreshGitHub(){')[1]?.split('function addVehicle(){')[0];
assert.ok(autoRefresh && !autoRefresh.includes('vehicles=incoming'), 'read-only refresh never overwrites phone data');
assert.ok(text.includes("if(fromGitHub && isBlankSeed(recs))"), 'blank GitHub import guard');
console.log('Safe-restoration tests passed.');
