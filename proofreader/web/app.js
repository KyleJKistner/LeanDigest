"use strict";
(() => {
  const $ = id => document.getElementById(id);
  let payload = JSON.parse($("proofreader-data").textContent);
  let doc = payload.document, current = null, filter = "all", tab = "reading";
  const text = (tag, value, cls) => { const e = document.createElement(tag); e.textContent = String(value ?? ""); if (cls) e.className = cls; return e; };
  const allSteps = ds => { const out = [], stack = [...ds].reverse(); while(stack.length) {const s = stack.pop();out.push(s);stack.push(...(s.children || []).slice().reverse()); if(out.length > 200000) throw Error("Reading tree too large");} return out; };
  const isSnapshot = d => d.evidence==="source-bound-snapshot";
  const isTyped = d => d.evidence==="typed-export" || isSnapshot(d);
  const hasGaps = d => allSteps(d.steps || []).some(s => s.fallback);
  const label = name => name.split(".").pop().replace(/_/g, " ");
  const say = message => {$("toast").textContent=message;$("toast").hidden=false;setTimeout(()=>$("toast").hidden=true,4500);};
  const clear = node => node.replaceChildren();
  function validate(d) {
    if (!d || d.schema !== "proofreader.document/v1" || !Array.isArray(d.declarations) || !Array.isArray(d.files)) throw Error("This is not a supported reading file.");
    if (d.declarations.length > 100000) throw Error("The file exceeds the browser declaration budget.");
    for(const x of d.declarations) {
      if(!x || typeof x.name !== "string" || typeof x.id !== "string" || !Array.isArray(x.steps)) throw Error("Invalid declaration.");
      allSteps(x.steps);
    }
    return d;
  }
  function counts() {
    const ds = doc.declarations, steps = allSteps(ds.flatMap(d => d.steps));
    return {files:doc.files.length, declarations:ds.length, typed:ds.filter(isTyped).length, snapshots:ds.filter(isSnapshot).length, gaps:steps.filter(s=>s.fallback).length, steps:steps.length, receipts:ds.filter(d=>d.receipt?.status==="passed").length};
  }
  function updateList() {
    const q = $("search").value.trim().toLowerCase();
    const selected = doc.declarations.filter(d => (filter!=="gaps" || hasGaps(d)) && (filter!=="typed" || isTyped(d)) && (!q || [d.name,d.file,d.statement,d.docstring].join(" ").toLowerCase().includes(q)));
    clear($("declaration-list"));
    for(const d of selected.slice(0,1000)) {
      const b = text("button", ""); b.dataset.id=d.id;b.classList.toggle("active",current?.id===d.id);b.setAttribute("aria-current",current?.id===d.id?"true":"false");
      b.append(text("span",label(d.name),"nav-name"));
      const discipline = d.file.replace(/^lean\/OAI\//,"").split("/").slice(0,-1).join(" / ");
      const gap = hasGaps(d);
      b.append(text("span",discipline || d.file,"nav-path"));
      b.append(text("span",(isSnapshot(d)?"Source-bound snapshot":(isTyped(d)?"Typed export":"Source outline")) + (gap?" · unexpanded steps":""),"nav-path"+(gap?" nav-gap":"")));
      b.addEventListener("click",()=>select(d.id));$("declaration-list").append(b);
    }
    $("library-count").textContent=`${selected.length} of ${doc.declarations.length} declarations`+(selected.length>1000?" · first 1,000 shown":"");
    $("empty").hidden=selected.length>0;
    $("reader").hidden=selected.length===0;
    if(selected.length && (!current || !selected.some(d=>d.id===current.id))) select(selected[0].id, false);
  }
  function select(id, refresh=true) {
    const d = doc.declarations.find(d=>d.id===id);if(!d)return;
    current=d;$("inspector").hidden=true;$("file-path").textContent=d.file;
    $("kind").textContent=d.kind;
    $("theorem-title").textContent=label(d.name);
    $("qualified-name").textContent=d.name;
    const typed=isTyped(d);
    const snapshot=isSnapshot(d);
    const kernel=d.axes?.proof==="path-bound-typed-judgements";
    $("evidence-badge").textContent=snapshot?"Source-bound snapshot":typed?"Typed export":"Source outline";
    $("trust-banner").textContent=typed?
      (kernel ? "Generated from the original proof expressions, with source-linked intermediate claims. English templates are not formally certified. " + (d.receipt?.status==="passed" ? "A successful external checking record is attached; this browser does not authenticate it." : "No successful intermediate-claim checking record is attached.") : "This view reports typed export data. Its English is not certified. Any imported build receipt must be independently reproduced; it is not authenticated by this reader."):
      "This is a deterministic source outline, not a checked English proof. It describes proof instructions; hidden goals and tactic derivations have not been reconstructed. No Lean verification was performed for this view.";
    if(snapshot) $("trust-banner").textContent="This mathematical reading is generated from a source-bound Lean snapshot. Formula text uses Lean’s pretty-printer; English semantics are not formally certified. "+(d.receipt?.status==="passed"?"A successful checking observation is attached, but this browser does not authenticate it.":"No successful re-extraction record is attached.");
    if(d.axes?.axiom_status?.acceptable===false) $("trust-banner").textContent += " AXIOM WARNING: additional or incomplete assumptions require review.";
    $("author-note").textContent=d.docstring ? "Author’s source note: "+d.docstring : "";
    clear($("parameters"));
    for(const p of d.parameters || []) {
      const row=text("div","","parameter");
      if(typeof p.text==="string") { row.append(text("span",p.text)); } else {
        row.append(text("span",p.binder==="["?"Assume the structure ":"Let "));
        row.append(text("code",p.names?`${p.names} : ${p.type}`:p.type));row.append(text("span","."));
      } $("parameters").append(row);
    }
    $("statement").textContent=d.statement || "No explicit statement recovered. Inspect the source or export from Lean.";
    $("context-box").hidden=!(d.context||[]).length;clear($("context"));
    for(const c of d.context||[])$("context").append(text("pre",c));
    $("argument-label").textContent=typed?"Proof":"Proof outline";
    $("reading-note").textContent=typed?"Each inference links to its original proof term and local assumptions. Inspect a step for evidence; expand its supporting argument where needed.":"Nested details follow source layout. Select a line reference for exact Lean text. Automation labels identify methods, not their hidden derivations.";
    if(snapshot) $("reading-note").textContent="Follow the two cases and expand intermediate claims. Inspect arithmetic steps for independently replayable integer-polynomial certificates. All exported frames are accounted for; named lemmas remain dependencies.";
    clear($("proof-steps"));
    (d.steps||[]).forEach((s,i)=>$("proof-steps").append(stepNode(s,String(i+1),0)));
    if(!d.steps.length)$("proof-steps").append(text("p","No proof steps recovered. Axioms and definitions may not contain a theorem proof.","muted"));
    $("exact-source").textContent=d.source || "The original source was not embedded; consult the typed export and pinned module.";
    clear($("dependencies"));
    for(const name of (d.dependencies || []).slice(0,250)) {
      const targets=doc.declarations.filter(x=>x.name===name || x.name.endsWith("."+name));
      if(targets.length===1){const b=text("button",name,"dependency");b.addEventListener("click",()=>{filter="all";$("search").value="";setFilters();select(targets[0].id);});$("dependencies").append(b);}
      else $("dependencies").append(text("span",name,"dependency unresolved"));
    }
    $("dependencies-section").hidden=!(d.dependencies||[]).length;
    renderAudit(d);setTab(tab);
    if(refresh)updateList();
    try { history.replaceState(null,"","#"+encodeURIComponent(id)); } catch (_) {}
  }
  function stepNode(s,num,depth) {
    if(depth>160)return text("p","Display depth limit reached. Inspect the exported JSON.","warning");
    const root=text("div","","step"+(s.fallback?" fallback":""));root.dataset.stepId=s.id;
    const head=text("div","","step-header");head.append(text("span",num,"step-number"));
    head.append(text("span",s.text,"step-title"+(s.text.length>240?" long":"")));
    const inspect=text("button",s.span?`L${s.span.line}`:"Inspect","step-inspect");inspect.setAttribute("aria-label",`Inspect step ${num}`);inspect.addEventListener("click",()=>inspectStep(s));head.append(inspect);root.append(head);
    if(s.conclusion && !s.text.includes(s.conclusion))root.append(text("div",s.conclusion,"step-conclusion"));
    if(s.fallback)root.append(text("div","Unexpanded · underlying expression retained; not counted as explained","step-flags"));
    if(s.supports?.length) {
      const links=text("div","Uses earlier steps: ","support-links");
      for(const id of s.supports) {
        const step=allSteps(current.steps||[]).find(t=>t.id===id);
        if(!step) {links.append(text("span","[missing support]","warning"));continue;}
        const b=text("button",step.rule.replace(/-/g," "),"support-link");
        b.addEventListener("click",()=>{
          const target=[...$("proof-steps").querySelectorAll("[data-step-id]")].find(e=>e.dataset.stepId===id);
          if(target) {let node=target.parentElement;while(node){if(node.tagName==="DETAILS")node.open=true;node=node.parentElement;}target.scrollIntoView({block:"center"});}
          inspectStep(step);
        });links.append(b);
      }root.append(links);
    }
    if(s.children?.length){const details=text("details","","step-children");if(s.evidence==="source-bound-snapshot" && ["cases","case","verify-conclusions"].includes(s.rule)) details.open=true;details.append(text("summary",`${s.children.length} supporting ${s.children.length===1?"step":"steps"}`));s.children.forEach((c,i)=>details.append(stepNode(c,String(i+1),depth+1)));root.append(details);}
    return root;
  }
  function inspectStep(s) {
    $("inspector").hidden=false;$("inspector-title").textContent=s.rule.replace(/-/g," ");
    $("inspector-evidence").textContent=(s.evidence || "source")+(s.span?` · lines ${s.span.line}–${s.span.end_line}`:"")+(s.term_id?` · term ${s.term_id}`:"");
    $("inspector-text").textContent=s.text;
    $("inspector-source").textContent=s.source || s.conclusion || "No source text attached to this exported term.";
    $("inspector-detail").textContent=s.detail || (s.evidence==="source"?"The source is authoritative for what was written, not evidence that the mathematical inference has been checked.":"Typed metadata depends on the correctness of the exporter. English fidelity is not certified.");
    clear($("inspector-context"));
    if(s.context?.length){$("inspector-context").append(text("h4","Exported local context"));for(const c of s.context)$("inspector-context").append(text("pre",`${c.name} : ${c.type}`,"muted"));}
  }
  function auditRow(title,value) {const d=text("div","","audit-row");d.append(text("b",title),text("span",value));return d;}
  function renderAudit(d) {
    const a=$("audit");clear(a);
    a.append(auditRow("Discovery",d.axes?.discovery || d.evidence));
    a.append(auditRow("Mathematical statement",d.axes?.statement || "Source statement; not elaborated"));
    a.append(auditRow("Proof evidence",d.receipt?"An external build receipt is attached. Re-run it before relying on it.":"No successful local Lean build receipt is attached."));
    a.append(auditRow("English fidelity","Not certified. The reader is a tested deterministic printer, not a formally verified English semantics."));
    if(d.axes?.proof==="path-bound-typed-judgements") {
      a.append(auditRow("Intermediate claims",d.receipt?.status==="passed" && d.receipt?.all_judgements_kernel_checked ? "External record reports all typed claims accepted by the Lean kernel." : "Checking source generated; no successful all-claims checking record attached."));
      a.append(auditRow("Original-proof linkage",d.receipt?.status==="passed" && d.receipt?.path_linkage_checked_in_lean ? "External record reports independently replayed original proof paths." : "Paths validated structurally; native rechecking still required."));
      a.append(auditRow("Receipt authenticity","Not authenticated. Re-run the exact checking source in the pinned environment."));
      a.append(auditRow("Lean version",d.receipt?.lean_version || d.axes.lean_version || doc.provenance?.lean_version || "See export"));
      const axs=d.axes.axiom_status?.axioms;
      a.append(auditRow("Transitive axioms",Array.isArray(axs)?(axs.length?axs.join(", "):"None reported by Lean"):"Consult raw export"));
      a.append(auditRow("Argument SHA-256",d.axes.argument_sha256));
      if(d.axes.fully_quantified_statement) {const details=text("details","");details.append(text("summary","Full quantified statement"),text("pre",d.axes.fully_quantified_statement,"formula"));a.append(details);}
    }
    if(isSnapshot(d)) {
      a.append(auditRow("Evidence route","Source-bound formula snapshot; not the raw constructor-DAG renderer."));
      a.append(auditRow("Selected original-proof judgements",d.receipt?.status==="passed" && d.receipt?.all_selected_judgements_kernel_checked ? String(d.receipt.selected_judgements)+" selected original proof subterms were accepted by Lean in the attached observation." : "No successful checking observation attached."));
      a.append(auditRow("Frames accounted for",String(Object.keys(d.axes.frame_owners||{}).length)));
      a.append(auditRow("Polynomial certificates",String(d.axes.polynomial_certificates||0)+" exact integer-polynomial identities, under recorded local assumptions."));
      a.append(auditRow("Snapshot SHA-256",d.axes.snapshot_sha256));
      a.append(auditRow("Lean version",d.axes.lean_version));
      a.append(auditRow("Transitive axioms",(d.axes.axiom_status?.axioms||[]).join(", ")||"None reported"));
      a.append(auditRow("Receipt authenticity","Not authenticated. Re-extract the original source and compare the complete snapshot."));
    }
    a.append(auditRow("Source integrity",doc.files.find(f=>f.path===d.file)?.sha256 || "No source hash attached"));
    for(const w of d.warnings||[])a.append(text("p",w,"warning"));
    if(d.receipt){const details=text("details","");details.append(text("summary","Inspect recorded receipt"),text("pre",JSON.stringify(d.receipt,null,2),"source-block"));a.append(details);}
  }
  function setTab(name) {tab=name;for(const t of ["reading","source","audit"]){$("panel-"+t).hidden=t!==name;$("tab-"+t).setAttribute("aria-selected",String(t===name));}}
  function setFilters(){for(const b of $("filters").querySelectorAll("button"))b.setAttribute("aria-pressed",String(b.dataset.filter===filter));}
  function coverage(){const c=counts();clear($("coverage-summary"));const grid=text("div","","metric-grid");
    for(const [n,l] of [[c.declarations,"declarations indexed"],[c.typed,"Lean-derived reading records"],[0,"certified English proofs"]]){const metric=text("div","","metric");metric.append(text("strong",n),text("span",l));grid.append(metric);}$("coverage-summary").append(grid);
    $("coverage-summary").append(text("p",`${c.files} input files · ${c.snapshots} source-bound snapshots · ${c.steps} displayed steps · ${c.gaps} explicitly unexpanded steps · ${c.receipts} attached successful external records. These are display counts, not a whole-corpus coverage claim. Records are not authenticated by this browser.`,"muted"));
    $("coverage-summary").append(text("p","No human comprehension study has been performed. Recognizing a tactic name is not equivalent to explaining its mathematical derivation.","warning"));
    $("provenance").textContent=JSON.stringify(doc.provenance||{},null,2);$("coverage-dialog").showModal();}
  function downloadDocument(){const b=new Blob([JSON.stringify(doc,null,2)],{type:"application/json"});const u=URL.createObjectURL(b);const a=text("a","");a.href=u;a.download="proofreader.document.json";a.click();setTimeout(()=>URL.revokeObjectURL(u),2000);}
  $("search").addEventListener("input",updateList);
  $("filters").addEventListener("click",e=>{const b=e.target.closest("button");if(b){filter=b.dataset.filter;setFilters();updateList();}});
  document.querySelectorAll(".tabs button").forEach(b=>b.addEventListener("click",()=>setTab(b.dataset.tab)));
  $("expand-btn").addEventListener("click",()=>$("proof-steps").querySelectorAll("details").forEach(d=>d.open=true));
  $("collapse-btn").addEventListener("click",()=>$("proof-steps").querySelectorAll("details").forEach(d=>d.open=false));
  $("inspector-close").addEventListener("click",()=>$("inspector").hidden=true);
  $("coverage-btn").addEventListener("click",coverage);$("dialog-close").addEventListener("click",()=>$("coverage-dialog").close());
  $("coverage-dialog").addEventListener("click",e=>{if(e.target===$("coverage-dialog"))$("coverage-dialog").close();});
  $("export-btn").addEventListener("click",downloadDocument);$("import-btn").addEventListener("click",()=>$("import-file").click());
  $("import-file").addEventListener("change",async e=>{try {const f=e.target.files[0];if(!f)return;if(f.size>64000000)throw Error("Use the CLI for reading files above 64 MB.");let input; if(f.name.endsWith(".lean")){if(location.protocol!=="http:" || location.hostname!=="127.0.0.1")throw Error("To open Lean source, start the local parser with: leanglish serve. Offline HTML can open reading JSON files.");const response=await fetch("/api/read",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({name:f.name,source:await f.text()})});input=await response.json();if(!response.ok)throw Error(input.error||"Source parsing failed");}else{input=JSON.parse(await f.text());}doc=validate(input.document||input);current=null;filter="all";$("search").value="";setFilters();$("library-title").textContent=doc.title;updateList();say("Reading file opened. Imported receipts have not been authenticated.");}catch(err){say(err.message);}finally{e.target.value="";}});
  document.addEventListener("keydown",e=>{if(e.key==="Escape")$("inspector").hidden=true;});
  try {validate(doc);$("library-title").textContent=doc.title;const id=decodeURIComponent(location.hash.slice(1));current=doc.declarations.find(d=>d.id===id)||doc.declarations[0]||null;updateList();if(current)select(current.id);}catch(err){say(err.message);}
})();
