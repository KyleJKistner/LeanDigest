(() => {
  'use strict';
  const data = JSON.parse(document.getElementById('argument-data').textContent);
  const $ = id => document.getElementById(id);
  const text = (tag, value, cls) => {const node = document.createElement(tag);node.textContent=value;if(cls)node.className=cls;return node;};
  const clear = node => node.replaceChildren();
  const button = (label, action, cls) => {const b=text('button',label,cls);b.type='button';b.addEventListener('click',action);return b;};
  const plans = new Map();
  let item=null, frame=0, parents=new Map();
  const roles={introduce:'Parameter introduction',assume:'Assumption',have:'Local fact',define:'Local definition',
    given:'Local proof reference','local-application':'Local lemma application',named:'Named result',application:'Application',
    combine:'Conjunction',choose:'Witness elimination',witness:'Witness construction',cases:'Case split',
    chain:'Calculation',cancel:'Cancellation',rewrite:'Unexpanded rewrite',ring:'Unexpanded ring calculation',
    unexpanded:'Unexpanded proof',reflexivity:'Reflexivity',identity:'Identity',induction:'Induction',
    congruence:'Congruence',specialize:'Specialization'};
  const f = i => item.snapshot.frames[i];
  const valid = i => Number.isSafeInteger(i) && i>=0 && i<item.snapshot.frames.length;
  const say = s => {$('status').textContent=s;};
  function sync(replace=false) {
    const url=new URL(location.href);url.searchParams.set('proof',item.id);url.searchParams.set('frame',String(frame));
    history[replace?'replaceState':'pushState'](null,'',url);
  }
  function proofList() {
    const q=$('search').value.trim().toLocaleLowerCase();clear($('proof-list'));
    const matches=data.items.filter(x=>x.snapshot.theorem.toLocaleLowerCase().includes(q));
    $('empty').hidden=matches.length>0;$('reader').hidden=matches.length===0;
    for(const x of matches){const b=button(x.snapshot.theorem,()=>select(x.id,null,true));b.dataset.proof=x.id;b.setAttribute('aria-current',String(x.id===item?.id));$('proof-list').append(b);}
    if(matches.length && !matches.some(x=>x.id===item?.id))select(matches[0].id,null,false);
  }
  function select(id, chosen=null, push=false) {
    const next=data.items.find(x=>x.id===id);if(!next)return;
    item=next;parents=new Map();for(const x of item.snapshot.frames)for(const c of x.children)parents.set(c,x.id);
    frame=chosen!==null && valid(chosen)?chosen:item.index.entry;
    $('theorem-name').textContent=item.snapshot.theorem;$('snapshot-hash').textContent=item.id;
    $('lean-box').hidden=!item.source;
    $('lean-path').textContent=item.source?.path||'';$('lean-source').textContent=item.source?.source||'';
    $('binding-dialog').close();$('plan-message').textContent='';render();sync(!push);proofList();
  }
  function visit(i, push=true) {
    if(!valid(i))return;frame=i;$('binding-dialog').close();render();if(push)sync();
    $('goal').focus({preventScroll:true});
  }
  function inputLabel(parent, child) {
    if(parent.role==='have')return child===parent.children[0]?'Proof of '+parent.binder:'Continuation with '+parent.binder;
    if(['introduce','assume','define'].includes(parent.role))return 'Body under '+parent.binder;
    const p=parent.premises.find(x=>x.frame===child);
    return p?'Premise':'Source subproof';
  }
  function showBinding(id) {
    const origin=f(id), binding=item.index.bindings.find(b=>b.frame===id);if(!binding)return;
    $('binding-title').textContent=origin.binder;$('binding-type').textContent=origin.domain;
    $('binding-kind').textContent=roles[origin.role]+(origin.value!==undefined?' · '+origin.value:'');
    clear($('binding-origin'));$('binding-origin').append(button('Introduction · step '+id,()=>visit(id)));
    if(binding.proof!==null)$('binding-origin').append(button('Proof · step '+binding.proof,()=>visit(binding.proof)));
    clear($('binding-uses'));
    for(const i of binding.recorded_references)$('binding-uses').append(button('Step '+i+' · '+f(i).statement,()=>visit(i)));
    if(!binding.recorded_references.length)$('binding-uses').append(text('p','No explicit local-proof reference recorded.','note'));
    $('binding-dialog').showModal();
  }
  function render() {
    const current=f(frame), indexed=item.index.nodes[frame];
    $('goal').textContent=current.statement;$('frame-label').textContent='Step '+frame;
    $('goal-heading').textContent=frame===0?'Statement':'Goal';
    $('operation').textContent=(roles[current.role]||current.role)+(current.head?' · '+current.head:'')+(current.budget_cut?' · Snapshot expansion stopped here.':'');
    $('source-frame').textContent=JSON.stringify(current,null,2);$('source-path').textContent='Original proof path: ['+current.path.join(', ')+']';
    $('parent-button').disabled=!parents.has(frame);
    clear($('breadcrumb'));let chain=[],cursor=frame;while(parents.has(cursor)){cursor=parents.get(cursor);chain.push(cursor);}chain.reverse();
    for(const i of chain)$('breadcrumb').append(button(String(i),()=>visit(i)));
    $('breadcrumb').append(text('span',String(frame)));
    clear($('inputs'));
    for(const child of current.children){const card=button('',()=>visit(child),'input-card');card.dataset.frame=String(child);card.append(text('span',inputLabel(current,child),'input-label'),text('span',f(child).statement,'input-claim'));$('inputs').append(card);}
    $('input-note').textContent=current.children.length?'Inputs retain their original local context.':(current.role==='given'?'This step refers to a local proof.':'No proof inputs were expanded in this snapshot.');
    clear($('reference'));
    if(indexed.reference){const r=indexed.reference;if(r.status==='resolved')$('reference').append(button('Inspect '+f(r.binder).binder,()=>showBinding(r.binder)));
      else {$('reference').append(text('p',r.status==='ambiguous'?'The snapshot does not distinguish these same-named hypotheses.':'The local reference could not be resolved.','warning'));for(const id of r.candidates)$('reference').append(button(f(id).binder+' · introduction '+id,()=>showBinding(id)));}}
    clear($('context'));
    for(const id of indexed.scope){const origin=f(id),row=text('div','','context-row');row.dataset.binder=String(id);row.append(button(origin.binder,()=>showBinding(id)),text('span',origin.domain,'context-type'));$('context').append(row);}
    if(!indexed.scope.length)$('context').append(text('p','No local context.','note'));
    clear($('facts'));const facts=item.index.bindings.filter(b=>['have','define'].includes(f(b.frame).role));
    for(const b of facts){const origin=f(b.frame);$('facts').append(button(origin.binder+' : '+origin.domain,()=>visit(b.proof??b.frame)));}
    $('facts-box').hidden=!facts.length;renderPlan();
  }
  function renderPlan() {
    const plan=plans.get(item.id)||[];clear($('plan'));$('plan-count').textContent=plan.length?'('+plan.length+')':'';
    plan.forEach((id,k)=>{const row=text('li','');row.append(button('Step '+id,()=>visit(id),'plan-name'));
      const up=button('↑',()=>move(k,-1));up.setAttribute('aria-label','Move step '+id+' earlier');up.disabled=k===0;
      const down=button('↓',()=>move(k,1));down.setAttribute('aria-label','Move step '+id+' later');down.disabled=k===plan.length-1;
      row.append(up,down,button('Remove',()=>{plan.splice(k,1);renderPlan();}));$('plan').append(row);});
    $('pin-button').disabled=plan.includes(frame);$('download-plan').disabled=!plan.length;$('clear-plan').disabled=!plan.length;
  }
  function move(k, direction) {const p=plans.get(item.id);if(!p||k+direction<0||k+direction>=p.length)return;[p[k],p[k+direction]]=[p[k+direction],p[k]];renderPlan();}
  function download(name,value) {const blob=new Blob([value],{type:'application/json;charset=utf-8'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=name;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);}
  $('search').addEventListener('input',proofList);
  $('import-plan').addEventListener('click',()=>$('plan-file').click());
  $('plan-file').addEventListener('change',async()=>{
    const file=$('plan-file').files[0];if(!file)return;
    // Bind asynchronous reads to the selected proof; switching proofs must not
    // attach a plan to whichever proof happens to be active when the read ends.
    const target=item.id;$('plan-message').textContent='';
    try {
      if(file.size>65536)throw Error('Reading-order file is too large.');
      const value=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(await file.arrayBuffer()));
      if(item.id!==target)throw Error('The selected proof changed. Open the reading order again.');
      if(!value||typeof value!=='object'||Array.isArray(value)||Object.keys(value).sort().join(',')!=='frames,schema,snapshot_sha256')throw Error('A reading order contains only source references.');
      if(value.schema!=='leanglish.reading-plan/v1'||value.snapshot_sha256!==target)throw Error('This reading order belongs to a different proof.');
      if(!Array.isArray(value.frames)||value.frames.length>1000||value.frames.some(i=>!valid(i))||new Set(value.frames).size!==value.frames.length)throw Error('Invalid or repeated source steps.');
      plans.set(target,[...value.frames]);renderPlan();$('plan-message').textContent='Reading order loaded.';
    } catch(error) {$('plan-message').textContent=error.message;}
    $('plan-file').value='';
  });
  $('statement-button').addEventListener('click',()=>visit(0));$('parent-button').addEventListener('click',()=>visit(parents.get(frame)));
  $('pin-button').addEventListener('click',()=>{const p=plans.get(item.id)||[];if(!p.includes(frame))p.push(frame);plans.set(item.id,p);$('plan-box').open=true;renderPlan();say('Step added to reading order.');});
  $('clear-plan').addEventListener('click',()=>{plans.set(item.id,[]);renderPlan();});
  $('download-plan').addEventListener('click',()=>download('reading-order.json',JSON.stringify({schema:'leanglish.reading-plan/v1',snapshot_sha256:item.id,frames:plans.get(item.id)||[]},null,2)+'\n'));
  $('download-snapshot').addEventListener('click',()=>download('snapshot.json',JSON.stringify(item.snapshot,null,2)+'\n'));
  $('close-dialog').addEventListener('click',()=>$('binding-dialog').close());
  function restore(){const params=new URLSearchParams(location.search),id=params.get('proof'),s=params.get('frame');let selected=s!==null&&/^(0|[1-9][0-9]*)$/.test(s)?Number(s):null;
    const next=data.items.find(x=>x.id===id)||data.items[0];$('search').value='';select(next.id,selected,false);}
  window.addEventListener('popstate',restore);
  $('proof-count').textContent=data.items.length+' proofs';restore();
})();
