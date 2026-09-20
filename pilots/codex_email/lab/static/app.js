"use strict";
const $ = (id) => document.getElementById(id);
let token = sessionStorage.getItem("moraine.operator") || "";
if (location.hash.length > 1) {
  token = location.hash.slice(1);
  history.replaceState(null, "", location.pathname);
  sessionStorage.setItem("moraine.operator", token);
}
let state = {run: null}, busy = false;
let pollTimer;
const names = {pending:"Attente de décision",accepted:"Accepté",rejected:"Refusé",denied:"Interdit",unknown:"Résultat incertain",failed:"Échec fournisseur"};
function text(id, value) { $(id).textContent = value ?? ""; }
function element(tag, value, className) { const n=document.createElement(tag); if(value!==undefined)n.textContent=value; if(className)n.className=className; return n; }
function notice(message, error=false) { text("notice", message); $("notice").classList.toggle("error", error); }
async function api(path, payload) {
  const response = await fetch(path, {method:payload ? "POST" : "GET",headers:{"Authorization":"Bearer "+token,...(payload?{"Content-Type":"application/json"}:{})},...(payload?{body:JSON.stringify(payload)}:{})});
  const value=await response.json();
  if(!response.ok) throw new Error(value.error || "Erreur HTTP "+response.status);
  return value;
}
function render() {
  const r=state.run;
  text("run-id",r?"Exécution "+r.run_id+" · intervention : "+r.actor:"Aucune exécution active");
  text("state",names[r?.request?.state] || r?.request?.state || "Prêt");
  text("attempts",r?.attempts || 0);text("effects",r?.effects || 0);
  text("checks-count",r?.checks.filter(c=>c.passed).length || 0);
  text("source-title",r?.source_message.title);text("source-from",r?.source_message.from_address);text("source-body",r?.source_message.text);
  text("context",r?.context?.text || "Aucune lecture MCP.");
  const preview=r?.review?.snapshot?.prepared_reply?.preview;
  text("review",preview ? "À : "+preview.to+"\nObjet : "+preview.subject+"\n\n"+preview.body_text : "Aucune revue chargée.");
  $("received").replaceChildren();
  if(!r?.received.length) $("received").append(element("p","Aucun message reçu.","empty"));
  for(const m of r?.received || []) {
    const box=element("article",undefined,"delivery");
    box.append(element("h3",m.subject),element("p","À : "+m.to,"muted"),element("pre",m.body,"message"),element("p","SHA-256 · "+m.sha256,"digest"));
    $("received").append(box);
  }
  $("checks").replaceChildren(...(r?.checks || []).map(c=>element("div",(c.passed?"✓ ":"ÉCHEC · ")+c.name,"check"+(c.passed?"":" failed"))));
  text("processes",Object.entries(r?.processes||{}).map(([name,p])=>name+" · PID "+p.pid+" · "+(p.running?"en cours":"arrêté")).join("   /   "));
  $("events").replaceChildren(...(r?.events || []).slice().reverse().map(e=>{const n=element("details",undefined,"event");n.append(element("summary",String(e.sequence).padStart(2,"0")+" · "+e.kind+" · "+new Date(e.at*1000).toLocaleTimeString()),element("pre",JSON.stringify(e.data,null,2)));return n;}));
  document.querySelectorAll("button").forEach(b=>b.disabled=busy);
  $("approve").disabled=$("reject").disabled=busy || !preview || r?.request?.state!=="pending";
  $("campaign").disabled=busy || state.campaign?.status==="running";
  const campaign=state.campaign;
  text("campaign-status",campaign ? ({running:"En cours",passed:"Réussie",failed:"Échec",cancelled:"Interrompue"}[campaign.status]+" · "+campaign.results.length+" / 9 scénarios"+(campaign.error?" · "+campaign.error:"")) : "Aucune campagne exécutée.");
  $("campaign-results").replaceChildren(...(campaign?.results || []).map(row=>element("p",(row.passed?"✓ ":"ÉCHEC · ")+row.scenario+" · tentatives/effets : "+(row.attempts??"?")+"/"+(row.effects??"?")+(row.error?" · "+row.error:""),"check"+(row.passed?"":" failed"))));
  clearTimeout(pollTimer);
  if(campaign?.status==="running")pollTimer=setTimeout(()=>{if(busy)render();else refresh().catch(e=>notice(e.message,true));},1200);
}
async function refresh() { state=await api("/api/state"); render(); }
async function action(name, extra={}) {
  if(busy)throw new Error("Une opération est déjà en cours.");
  busy=true;render();notice("Opération en cours…");
  try { state=await api("/api/action",{action:name,run_id:state.run?.run_id??null,...extra}); if(name==="new")$("reply").value="";notice("Opération terminée."); }
  catch(e) { notice(e.message,true);try{state=await api("/api/state");}catch(_){} throw e; }
  finally {busy=false;render();}
  return {run_id:state.run?.run_id,request:state.run?.request,context:state.run?.context};
}
async function connect() {
  try {await refresh();$("login").hidden=true;$("workspace").hidden=false;notice("");}
  catch(e) {$("login").hidden=false;$("workspace").hidden=true;$("token").setCustomValidity("Jeton invalide ou console inaccessible.");$("token").reportValidity();}
}
$("login").addEventListener("submit",e=>{e.preventDefault();token=$("token").value;sessionStorage.setItem("moraine.operator",token);$("token").value="";$("token").setCustomValidity("");connect();});
$("token").addEventListener("input",()=>$("token").setCustomValidity(""));
const clickAction=(name,extra)=>action(name,extra).catch(()=>{}); // Error already displayed by action().
$("new").addEventListener("click",()=>clickAction("new",{actor:$("actor").value,provider_mode:$("mode").value}));
$("propose").addEventListener("click",()=>clickAction("propose",{body:$("reply").value}));
$("campaign").addEventListener("click",()=>clickAction("campaign"));
document.querySelectorAll("[data-action]").forEach(b=>b.addEventListener("click",()=>clickAction(b.dataset.action)));
if(token)connect();

// Optional browser-native tools share the visible actions. Approval remains an
// explicit operator action, outside this small agent tool surface.
if(document.modelContext?.registerTool) {
  const lifecycle=new AbortController();
  addEventListener("pagehide",()=>lifecycle.abort(),{once:true});
  const definitions=[
    {name:"read_delegated_message",description:"Read the selected fictional message through the real MCP facade and display it.",properties:{},required:[],
      execute:()=>action("read")},
    {name:"stage_reply_for_review",description:"Propose a reply through MCP and update the console. This does not approve or send it.",properties:{body:{type:"string",minLength:1}},required:["body"],
      execute:input=>{if(typeof input.body!=="string" || !input.body.trim() || new TextEncoder().encode(input.body).length>16384)throw new Error("invalid_reply");$("reply").value=input.body;return action("propose",{body:input.body});}}
  ];
  for(const definition of definitions) {
    const {properties,required,execute,...metadata}=definition;
    const tool={...metadata,inputSchema:{type:"object",properties,required,additionalProperties:false},annotations:{readOnlyHint:false,untrustedContentHint:true},execute:async input=>{
      if(!input || typeof input!=="object" || Array.isArray(input) || Object.keys(input).some(k=>!Object.hasOwn(properties,k)))throw new Error("invalid_input");
      return execute(input);
    }};
    try { Promise.resolve(document.modelContext.registerTool(tool,{signal:lifecycle.signal})).catch(()=>notice("Outils navigateur indisponibles; les boutons restent utilisables.",true)); }
    catch(_) {notice("Outils navigateur indisponibles; les boutons restent utilisables.",true);}
  }
}
