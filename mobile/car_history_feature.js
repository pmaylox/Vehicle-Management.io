/* CAR_HISTORY_BEGIN */
// Embedded in both standalone mobile HTML entrypoints; no network dependency.
const HISTORY_SOURCES=['CARFAX Car Care','CARFAX Vehicle History Report','Shop / dealership','Other'];
const HISTORY_TYPES=['Accident / damage','Title / registration','Ownership','Odometer','Service','Recall','Other'];
function carHistoryDate(s){
 if(typeof s!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(s))return false;
 const d=new Date(s+'T12:00:00Z');
 return Number.isFinite(d.getTime())&&d.toISOString().slice(0,10)===s;
}
function nextHistoryReview(s){
 if(!carHistoryDate(s))return null;
 const year=Number(s.slice(0,4))+1,month=Number(s.slice(5,7));
 const day=Math.min(Number(s.slice(8)),new Date(Date.UTC(year,month,0)).getUTCDate());
 return String(year).padStart(4,'0')+'-'+String(month).padStart(2,'0')+'-'+String(day).padStart(2,'0');
}
function normalizeCarHistory(raw){
 const h=raw&&typeof raw==='object'&&!Array.isArray(raw)?raw:{};
 const events=(Array.isArray(h.events)?h.events:[])
 .filter(x=>x&&typeof x==='object'&&!Array.isArray(x)&&carHistoryDate(x.date))
 .map(x=>{
   const n=x.mileage===null||x.mileage===undefined||x.mileage===''?null:Number(x.mileage);
   return {date:x.date,category:String(x.category||'Other').slice(0,80),
     description:String(x.description||'').slice(0,1000),
     source:String(x.source||'Other').slice(0,100),
     mileage:n!==null&&Number.isSafeInteger(n)&&n>=0&&n<=900000000?n:null,
     recorded_by:'user'};
 });
 return {last_review_date:carHistoryDate(h.last_review_date)?h.last_review_date:null,
   review_source:String(h.review_source||'').slice(0,100),
   review_notes:String(h.review_notes||'').slice(0,2000),events};
}
function carHistoryDue(a){
 const next=nextHistoryReview(normalizeCarHistory(a.car_history).last_review_date);
 return !next||next<=localDate();
}
function carHistoryOpts(values,selected){
 return values.map(x=>'<option value="'+esc(x)+'"'+(selected===x?' selected':'')+'>'+esc(x)+'</option>').join('');
}
function saveCarHistory(a,history,notice){
 const index=vehicles.indexOf(a);
 if(index<0){alert('Vehicle selection changed. Select the correct vehicle and try again.');return false;}
 const changed=vehicles.map((item,i)=>i===index?{...item,car_history:normalizeCarHistory(history)}:item);
 try{localStorage.setItem(KEY,JSON.stringify({vehicles:changed,current}));}
 catch(e){hasStorage=false;alert('Could not save Car History. Your current vehicle records were not changed. Export a backup.');updateBanner();return false;}
 vehicles=changed;hasStorage=true;renderCarHistory();updateBanner();message(notice);
 return true;
}
function renderCarHistory(){
 const a=v(),el=$('carHistoryBody');
 if(!a){el.innerHTML=empty('Add or import a vehicle first.');return;}
 const h=normalizeCarHistory(a.car_history),next=nextHistoryReview(h.last_review_date);
 const due=!next||next<=localDate();
 const rows=h.events.map((event,index)=>({event,index}))
  .sort((x,y)=>y.event.date.localeCompare(x.event.date));
 const timeline=rows.slice(0,100).map(({event:r,index})=>
  '<div class="record"><div><h4>'+esc(r.category)+' · '+esc(r.description)+'</h4><small>'+
  esc(r.date)+' · '+esc(r.source)+(r.mileage==null?'':' · '+num(r.mileage)+' reported mi')+
  ' · User-entered</small></div><button class="btn outline" type="button" data-history-delete="'+index+'">Delete</button></div>'
 ).join('');
 el.innerHTML=
 '<div class="card feature-card"><h3 style="margin-top:0">Car History · '+esc(a.year)+' '+esc(a.name)+'</h3>'+
 (a.vin?'<p class="small muted">VIN: '+esc(a.vin)+'</p>':'<p class="small muted">VIN not recorded; manual history is still available.</p>')+
 '<div class="note '+(due?'':'info')+'"><strong>'+(due?'Annual review due':'Annual review up to date')+'</strong>'+
 '<div class="small">Last reviewed: '+esc(h.last_review_date||'Never')+' · Next: '+esc(next||'Review now')+'</div></div>'+
 '<p class="small muted">Use your own CARFAX Car Care account to review reported history. MileSage has no automatic CARFAX connection. Reported mileage here never changes your live odometer, service or fuel logs.</p>'+
 '<a class="btn secondary" style="display:inline-block;text-decoration:none" href="https://www.carfax.com/Service" target="_blank" rel="noopener noreferrer">Open CARFAX Car Care</a>'+
 '<form id="carHistoryReviewForm"><h4>Confirm annual history review</h4>'+
 '<label class="field" for="carReviewDate">Date reviewed</label><input type="date" id="carReviewDate" value="'+localDate()+'" required>'+
 '<label class="field" for="carReviewSource">Source reviewed</label><select id="carReviewSource">'+carHistoryOpts(HISTORY_SOURCES,h.review_source||HISTORY_SOURCES[0])+'</select>'+
 '<label class="field" for="carReviewNotes">Notes (optional)</label><textarea id="carReviewNotes" maxlength="2000">'+esc(h.review_notes)+'</textarea>'+
 '<button class="btn full" type="submit">Mark history reviewed</button></form>'+
 '<p class="small muted">The next reminder is one calendar year later, only after you confirm a review. This does not buy or download a CARFAX report.</p></div>'+
 '<div class="card"><h3 style="margin-top:0">Add reported history event</h3>'+
 '<p class="small muted">Enter findings from CARFAX or another source. This timeline is separate from MileSage maintenance and expenses.</p>'+
 '<form id="carEventForm"><label class="field" for="carEventDate">Event date</label><input type="date" id="carEventDate" value="'+localDate()+'" required>'+
 '<label class="field" for="carEventType">Event type</label><select id="carEventType">'+carHistoryOpts(HISTORY_TYPES,HISTORY_TYPES[0])+'</select>'+
 '<label class="field" for="carEventSource">Reported by</label><select id="carEventSource">'+carHistoryOpts(HISTORY_SOURCES,HISTORY_SOURCES[0])+'</select>'+
 '<label class="field" for="carEventMiles">Reported mileage (optional)</label><input id="carEventMiles" type="number" min="0" max="900000000" step="1" inputmode="numeric" placeholder="Leave blank if unknown">'+
 '<label class="field" for="carEventDescription">Description</label><textarea id="carEventDescription" maxlength="1000" required></textarea>'+
 '<button class="btn full" type="submit">Save history event</button></form></div>'+
 '<div class="card"><h3 style="margin-top:0">Reported history timeline ('+num(h.events.length)+')</h3>'+
 (timeline||empty('No history events recorded yet.'))+
 (rows.length>100?'<p class="small muted">Showing latest 100; all events remain in the backup.</p>':'')+'</div>';
 $('carHistoryReviewForm').onsubmit=e=>{
  e.preventDefault();
  try{
   const day=$('carReviewDate').value,source=$('carReviewSource').value;
   if(!validDate(day))throw Error('Enter a valid review date, not in the future.');
   if(!HISTORY_SOURCES.includes(source))throw Error('Choose a valid source.');
   const nextHistory=normalizeCarHistory(a.car_history);
   nextHistory.last_review_date=day;nextHistory.review_source=source;
   nextHistory.review_notes=$('carReviewNotes').value.trim().slice(0,2000);
   saveCarHistory(a,nextHistory,'History review recorded for '+a.name+'.');
  }catch(error){alert(error.message);}
 };
 $('carEventForm').onsubmit=e=>{
  e.preventDefault();
  try{
   const day=$('carEventDate').value,source=$('carEventSource').value,
    category=$('carEventType').value,description=$('carEventDescription').value.trim(),
    rawMileage=$('carEventMiles').value.trim();
   if(!validDate(day))throw Error('Enter a valid event date, not in the future.');
   if(!HISTORY_SOURCES.includes(source)||!HISTORY_TYPES.includes(category))throw Error('Choose a valid source and event type.');
   if(!description)throw Error('Describe the reported event.');
   const mileage=rawMileage===''?null:whole(rawMileage,'Reported mileage',0);
   if(mileage!==null&&mileage>900000000)throw Error('Reported mileage is too large.');
   const nextHistory=normalizeCarHistory(a.car_history);
   nextHistory.events.push({date:day,category,source,description:description.slice(0,1000),mileage,recorded_by:'user'});
   saveCarHistory(a,nextHistory,'History event saved for '+a.name+'.');
  }catch(error){alert(error.message);}
 };
 el.querySelectorAll('[data-history-delete]').forEach(button=>button.onclick=()=>{
  const index=Number(button.dataset.historyDelete);
  if(!Number.isInteger(index)||index<0||index>=h.events.length)return;
  if(!confirm('Delete this history event for '+a.name+'?'))return;
  const nextHistory=normalizeCarHistory(a.car_history);
  nextHistory.events.splice(index,1);
  saveCarHistory(a,nextHistory,'History event deleted.');
 });
}
/* CAR_HISTORY_END */
