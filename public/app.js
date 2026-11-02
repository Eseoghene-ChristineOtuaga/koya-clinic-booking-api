"use strict";
// Assessment-only client. The API key is supplied per browser tab, never bundled or persisted.
// A production patient app would use separate patient authentication, not a shared administrator key.
const $ = (s) => document.querySelector(s);
const state = { key: "", slots: [], provider: null, date: null, selected: null, lookupEmail: null, cursor: null };
const dateFmt = new Intl.DateTimeFormat(undefined, { weekday: "short", month: "short", day: "numeric" });
const longDateFmt = new Intl.DateTimeFormat(undefined, { weekday: "long", month: "long", day: "numeric", year: "numeric" });
const timeFmt = new Intl.DateTimeFormat(undefined, { hour: "numeric", minute: "2-digit" });
const tz = Intl.DateTimeFormat().resolvedOptions().timeZone || "your local time";
$("#timezone").textContent = "Times in " + tz;

const dateKey = (value) => {
  const d = new Date(value);
  return [d.getFullYear(), String(d.getMonth()+1).padStart(2, "0"), String(d.getDate()).padStart(2, "0")].join("-");
};
const readableDate = (v) => longDateFmt.format(new Date(v));
const readableTime = (v) => timeFmt.format(new Date(v));
function showMessage(selector, text, type = "error") {
  const node = $(selector);
  node.textContent = text;
  node.className = "form-message " + type;
}
function element(tag, className, text) {
  const e = document.createElement(tag);
  if (className) e.className = className;
  if (text != null) e.textContent = text;
  return e;
}
function api(path, options = {}) {
  if (!state.key) return Promise.reject(new Error("Enter your API access key first."));
  const headers = { "X-API-Key": state.key, ...options.headers };
  return fetch(path, { ...options, headers }).then(async (r) => {
    let data = {};
    try { data = await r.json(); } catch { /* no body */ }
    if (r.status === 401) {
      state.key = "";
      showAccess();
      throw new Error("Access key rejected. Please enter the current API key.");
    }
    if (!r.ok) {
      const error = new Error(data.error || "The request could not be completed.");
      error.status = r.status;
      error.retryAfter = r.headers.get("Retry-After");
      throw error;
    }
    return data;
  });
}
function showAccess() {
  const dialog = $("#access-dialog");
  if (!dialog.open) dialog.showModal();
  $("#access-key").value = "";
  $("#access-key").focus();
}
$("#access-dialog").addEventListener("cancel", (event) => { if (!state.key) event.preventDefault(); });
$("#access-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const key = $("#access-key").value.trim();
  if (!key) return;
  state.key = key;
  $("#access-error").textContent = "";
  try {
    await loadSlots();
    $("#access-dialog").close();
    $("#access-key").value = "";
  } catch (e) {
    $("#access-error").textContent = e.message;
  }
});
function uniqueProviders() {
  return Array.from(new Set(state.slots.map((s) => s.provider)));
}
async function loadSlots() {
  const data = await api("/slots");
  state.slots = (data.slots || []).filter((s) => new Date(s.start) > new Date());
  const providers = uniqueProviders();
  if (!providers.includes(state.provider)) state.provider = providers[0] || null;
  renderProviders();
  renderDates();
  renderSummary();
}
function renderProviders() {
  const root = $("#providers");
  root.replaceChildren();
  const providers = uniqueProviders();
  if (!providers.length) {
    root.append(element("p", "empty-hint", "There are no upcoming appointments right now. Please check back later."));
    $("#time-help").textContent = "No upcoming slots have been published.";
    return;
  }
  for (const provider of providers) {
    const count = state.slots.filter(s => s.provider === provider && s.available).length;
    const selected = state.provider === provider;
    const btn = element("button", "provider-card");
    btn.type = "button"; btn.setAttribute("aria-pressed", String(selected));
    const avatar = element("span", "avatar", provider.split(/\s+/).map(x=>x[0]).slice(-2).join("").toUpperCase());
    avatar.setAttribute("aria-hidden", "true");
    const body = element("span");
    body.append(element("span", "provider-name", provider), element("span", "provider-detail", count + " appointment" + (count === 1 ? "" : "s") + " available"));
    btn.append(avatar, body);
    if (selected) { const tick = element("span", "provider-check", "✓");tick.setAttribute("aria-hidden","true");btn.append(tick); }
    btn.addEventListener("click", () => { state.provider = provider; state.date = null; state.selected = null; renderProviders(); renderDates(); renderSummary(); });
    root.append(btn);
  }
}
function selectedSlots() {
  return state.slots.filter(s => s.provider === state.provider && s.available);
}
function renderDates() {
  const dates = [...new Set(selectedSlots().map(s=>dateKey(s.start)))].sort();
  if (!dates.includes(state.date)) { state.date = dates[0] || null;state.selected = null; }
  $("#time-help").textContent = state.provider ? "Choose an open time with " + state.provider + "." : "Select a clinician to view availability.";
  const root = $("#dates"); root.replaceChildren();
  for (const day of dates) {
    const first = selectedSlots().find(s=>dateKey(s.start) === day);
    const btn = element("button","date-button");
    btn.type="button";btn.setAttribute("aria-pressed",String(day===state.date));
    const date = new Date(first.start);
    btn.append(element("span", "", new Intl.DateTimeFormat(undefined,{weekday:"short"}).format(date)), element("strong","",new Intl.DateTimeFormat(undefined,{month:"short",day:"numeric"}).format(date)));
    btn.addEventListener("click",()=>{state.date=day;state.selected=null;renderDates();renderSummary()});
    root.append(btn);
  }
  renderTimes();
}
function renderTimes() {
  const root = $("#times");root.replaceChildren();
  const slots = selectedSlots().filter(s=>dateKey(s.start)===state.date).sort((a,b)=>new Date(a.start)-new Date(b.start));
  if (!slots.length) {root.append(element("p","empty-hint",state.provider ? "No open times for this clinician. Try another provider." : "Choose a clinician to see times."));return;}
  for(const s of slots){
    const btn=element("button","time-button",readableTime(s.start));
    btn.type="button";btn.setAttribute("aria-pressed",String(state.selected===s.id));
    btn.setAttribute("aria-label",readableTime(s.start)+" with "+s.provider);
    btn.addEventListener("click",()=>{state.selected=s.id;renderTimes();renderSummary()});
    root.append(btn);
  }
}
function selectedSlot(){return state.slots.find(s=>s.id===state.selected && s.available);}
function renderSummary(){
  const slot=selectedSlot();
  $("#summary-provider").textContent=state.provider || "Not selected";
  $("#summary-date").textContent=slot ? readableDate(slot.start) : "Not selected";
  $("#summary-time").textContent=slot ? readableTime(slot.start) : "Not selected";
  $("#book-button").disabled=!slot;
}
$("#booking-form").addEventListener("submit",async(event)=>{
  event.preventDefault();
  const slot=selectedSlot();
  if(!slot){showMessage("#book-message","Choose an available appointment time first.");return;}
  const button=$("#book-button");
  button.disabled=true;button.textContent="Confirming appointment…";
  showMessage("#book-message","","success");
  try{
    const booking=await api("/bookings",{method:"POST",headers:{"Content-Type":"application/json","Idempotency-Key":crypto.randomUUID()},body:JSON.stringify({slot_id:slot.id,name:$("#patient-name").value.trim(),email:$("#patient-email").value.trim()})});
    const desc=$("#confirmation-description");
    desc.textContent="Your appointment with "+slot.provider+" has been confirmed.";
    const details=$("#confirmation-details");details.replaceChildren();
    for(const [label,value] of [["Patient",booking.name],["Date",readableDate(slot.start)],["Time",readableTime(slot.start)],["Booking reference",booking.id]]){
      const row=element("div");const b=element("strong","",label+": ");row.append(b,document.createTextNode(value));details.append(row);
    }
    $("#confirm-dialog").showModal();
    $("#booking-form").reset();state.selected=null;
    await loadSlots();
  }catch(e){
    const extra=e.status===429 && e.retryAfter ? " Try again in "+e.retryAfter+" seconds." : "";
    showMessage("#book-message",e.message+extra);
    await loadSlots().catch(()=>{});
  }finally{
    button.replaceChildren(document.createTextNode("Confirm appointment "),element("span","","↗"));
    renderSummary();
  }
});
$("#confirmation-done").addEventListener("click",()=>$("#confirm-dialog").close());
async function lookupBookings(more=false){
  const root=$("#booking-results");
  if(!more){state.lookupEmail=$("#lookup-email").value.trim().toLowerCase();state.cursor=null;root.replaceChildren();}
  const params=new URLSearchParams({email:state.lookupEmail,limit:"5"});
  if(more && state.cursor)params.set("cursor",state.cursor);
  showMessage("#lookup-message","Looking up appointments…","success");
  try{
    const result=await api("/bookings?"+params);
    if(!result.bookings.length && !more)root.append(element("p","empty-hint","No bookings found for this email address."));
    for(const booking of result.bookings)root.append(createBookingResult(booking));
    state.cursor=result.next_cursor;
    $("#load-more").hidden=!state.cursor;
    showMessage("#lookup-message",result.bookings.length ? "" : (more ? "No more appointments." : ""),"success");
  }catch(e){showMessage("#lookup-message",e.message);$("#load-more").hidden=true;}
}
function createBookingResult(booking){
  const card=element("article","result-card");
  const slot=state.slots.find(s=>s.id===booking.slot_id);
  const title=slot ? slot.provider : "Appointment "+booking.slot_id;
  const head=element("div","result-head");
  head.append(element("strong","",title),element("span","status-pill "+(booking.status==="cancelled"?"cancelled":""),booking.status));
  card.append(head);
  card.append(element("div","result-details","Booked for "+booking.name+" · "+booking.email+"\nReference: "+booking.id));
  if(slot)card.append(element("div","result-details",readableDate(slot.start)+" · "+readableTime(slot.start)));
  if(booking.status==="confirmed"){
    const cancel=element("button","cancel-button","Cancel this appointment");
    cancel.type="button";
    cancel.addEventListener("click",async()=>{
      if(!window.confirm("Cancel this appointment? This will release the slot for someone else."))return;
      cancel.disabled=true;
      try{await api("/bookings/"+encodeURIComponent(booking.id),{method:"DELETE"});showMessage("#lookup-message","Appointment cancelled.","success");await loadSlots();await lookupBookings();}
      catch(e){showMessage("#lookup-message",e.message);cancel.disabled=false;}
    });
    card.append(cancel);
  }
  return card;
}
$("#lookup-form").addEventListener("submit",e=>{e.preventDefault();lookupBookings()});
$("#load-more").addEventListener("click",()=>lookupBookings(true));
document.addEventListener("visibilitychange",()=>{if(!document.hidden && state.key)loadSlots().catch(()=>{});});
showAccess();

// Lightweight sticky-nav transition. Passive scroll keeps interaction smooth.
const siteHeader = document.querySelector(".site-header");
function updateHeaderOnScroll(){siteHeader.classList.toggle("is-scrolled",window.scrollY>24);}
window.addEventListener("scroll",updateHeaderOnScroll,{passive:true});
updateHeaderOnScroll();
