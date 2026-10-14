pack[record_] := Module[{names={},cache=<||>,nm,lv,nf,tags,binders,node,path,arg,step},
nm[n_]:=Module[{key=ToString[n,InputForm],row,i},If[KeyExistsQ[cache,key],Return[cache[key]]];row=Switch[n["tag"],"anonymous",{0},"str",{1,nm[n["prefix"]],n["value"]},"num",{2,nm[n["prefix"]],n["value"]}];i=Length[names];AppendTo[names,row];AssociateTo[cache,key->i];i];
lv[n_]:=Switch[n["tag"],"zero",{0},"succ",{1,lv[n["of"]]},"max",{2,lv[n["left"]],lv[n["right"]]},"imax",{3,lv[n["left"]],lv[n["right"]]},"param",{4,nm[n["name"]]}];
tags={"bvar","sort","const","app","lam","forall","let","nat","str","proj"};
nf=<|"bvar"->{"index"},"sort"->{"level"},"const"->{"name","levels"},"app"->{"fn","arg"},"lam"->{"name","domain","body","binder"},"forall"->{"name","domain","body","binder"},"let"->{"name","type","value","body","nondep"},"nat"->{"value"},"str"->{"value"},"proj"->{"name","index","of"}|>;
binders={"explicit","implicit","strict-implicit","instance"};
node[n_]:=Prepend[Map[Function[f,Switch[f,"name",nm[n[f]],"level",lv[n[f]],"levels",lv/@n[f],"binder",First[FirstPosition[binders,n[f]]]-1,_,n[f]]],nf[n["tag"]]],First[FirstPosition[tags,n["tag"]]]-1];
path[p_]:=StringJoin[ToString/@p];arg[a_]:={path[a["path"]],a["term"],a["type"],a["is_proof"],Lookup[a,"step",Null]};
step[a_]:={path[a["path"]],a["term"],a["type"],a["is_proof"],a["children"],arg/@a["arguments"],Lookup[a,"domain_is_prop",Null],a["truncated"],Lookup[a,"frontier_reason",Null]};
With[{nodes=node/@record["exprs"],steps=step/@record["steps"]},<|"schema"->"proofreader.kernel-wire/v1","meta"->KeyDrop[record,{"exprs","steps"}],"names"->names,"nodes"->nodes,"steps"->steps|>]];
