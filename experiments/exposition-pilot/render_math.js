'use strict';
const fs=require('fs'),path=require('path');
const katex=require(path.resolve(__dirname,'../../docs/companion/assets/katex.min.js'));
const xs=JSON.parse(fs.readFileSync(0,'utf8'));
process.stdout.write(JSON.stringify(xs.map(x=>katex.renderToString(x.tex,{displayMode:x.display,
  output:'mathml',throwOnError:true,trust:false,strict:'error'}))));
