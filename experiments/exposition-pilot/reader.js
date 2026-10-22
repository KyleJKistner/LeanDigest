(() => {
 'use strict';
 const data=JSON.parse(document.getElementById('reader-data').textContent);
 const $=id=>document.getElementById(id);
 function select(id){if(!data.articles.some(a=>a.id===id))id=data.articles[0].id;
  for(const a of data.articles){$(a.id).hidden=a.id!==id;document.querySelector(`[data-open="${a.id}"]`).setAttribute('aria-selected',String(a.id===id));}
  document.title=data.articles.find(a=>a.id===id).title+' | Leanglish';}
 for(const b of document.querySelectorAll('[data-open]'))b.onclick=()=>{location.hash=b.dataset.open;select(b.dataset.open);};
 window.addEventListener('hashchange',()=>select(location.hash.slice(1)));select(location.hash.slice(1));
 for(const b of document.querySelectorAll('[data-code]'))b.onclick=()=>{const article=b.closest('article');for(const q of article.querySelectorAll('[data-code]'))q.setAttribute('aria-pressed',String(q===b));for(const pane of article.querySelectorAll('.code-pane'))pane.hidden=pane.id!==b.dataset.code;};
 function download(name,value){const u=URL.createObjectURL(new Blob([value],{type:'text/plain;charset=utf-8'}));const a=document.createElement('a');a.href=u;a.download=name;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(u),500);}
 for(const b of document.querySelectorAll('[data-download]'))b.onclick=()=>{const id=b.dataset.download;download(id+'.lean',data.sources[id]);};
 // Integer examples use exact BigInt arithmetic. They are illustrations, not a proof oracle.
 function integer(s){if(!/^-?\d{1,12}$/.test(s.trim()))throw Error('Enter integers of at most twelve digits.');return BigInt(s.trim());}
 function egcd(a,b){let r=a<0n?-a:a,s=b<0n?-b:b,u=1n,v=0n,u1=0n,v1=1n;while(s!==0n){let q=r/s;[r,s]=[s,r-q*s];[u,u1]=[u1,u-q*u1];[v,v1]=[v1,v-q*v1];}return [r,a<0n?-u:u,b<0n?-v:v];}
 function bezout(){let out=$('bezout-output');try{const x=integer($('bx').value),y=integer($('by').value),z=integer($('bz').value);if(x*y!==z*(z+1n))throw Error('The hypothesis xy = z(z+1) is not satisfied.');const [g,r,s]=egcd(x,z);let a,d,b,c;if(g===0n){[a,d,b,c]=[1n,y,0n,1n];}else{[a,d,b,c]=[x/g,z/g,g,r*(z+1n)+s*y];}if(a*b!==x||d*c!==y||d*b!==z||a*c-d*b!==1n)throw Error('Example verification failed.');out.className='';out.dataset.valid='true';out.dataset.tuple=[a,d,b,c].map(String).join(',');out.textContent=`(a, d, b, c) = (${a}, ${d}, ${b}, ${c})\nab = ${a*b},   dc = ${d*c},   db = ${d*b},   ac − db = ${a*c-d*b}`;}catch(e){out.className='error';out.dataset.valid='false';delete out.dataset.tuple;out.textContent=e.message;}}
 $('bezout-run').onclick=bezout;bezout();
 function reversal(){const n=Number($('reverse-length').value);const slider=$('reverse-position');slider.max=String(n-1);if(Number(slider.value)>=n)slider.value=String(n-1);const i=Number(slider.value),j=n-1-i;const xs=Array.from({length:n},(_,k)=>String.fromCharCode(97+k));$('reverse-sequence').textContent=`X      = (${xs.join(', ')})\nrev X  = (${[...xs].reverse().join(', ')})\nrev² X = (${xs.join(', ')})`;$('reverse-output').textContent=`Position ${i} → ${j} → ${n-1-j}`;$('reverse-output').dataset.returned=String(n-1-j);}
 $('reverse-length').oninput=reversal;$('reverse-position').oninput=reversal;reversal();
 const bits=[[1,0,1,0],[1,1,0,0],[0,1,0,1],[1,0,0,1]];
 function diagonal(){const tbody=$('diagonal-body');tbody.replaceChildren();for(let i=0;i<4;i++){const tr=document.createElement('tr');const h=document.createElement('th');h.textContent=`f(${i})`;h.scope='row';tr.append(h);for(let j=0;j<4;j++){const td=document.createElement('td'),b=document.createElement('button');b.textContent=String(bits[i][j]);b.setAttribute('aria-label',`Membership of ${j} in f(${i}): ${bits[i][j]}`);b.dataset.row=i;b.dataset.col=j;if(i===j)td.className='diag';b.onclick=()=>{bits[i][j]=1-bits[i][j];diagonal();};td.append(b);tr.append(td);}tbody.append(tr);}const d=bits.map((r,i)=>1-r[i]);const tr=document.createElement('tr');tr.className='drow';const h=document.createElement('th');h.textContent='D';tr.append(h);for(const v of d){const td=document.createElement('td');td.textContent=v;tr.append(td);}tbody.append(tr);$('diagonal-output').textContent='D = {'+d.flatMap((b,i)=>b?[String(i)]:[]).join(', ')+'}';$('diagonal-output').dataset.bits=d.join('');}
 diagonal();
})();
