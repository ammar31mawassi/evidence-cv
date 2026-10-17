// Invoke the companion repository's real scoring module, with public read-only API data.
import { createRequire } from 'node:module';
import { resolve } from 'node:path';
import { writeFileSync } from 'node:fs';
const [analyzer,owner,output]=process.argv.slice(2);
if(!analyzer || !/^[a-zA-Z0-9-]+$/.test(owner??'') || !output) throw Error('Usage: node integrations/github-health.mjs ANALYZER_PATH OWNER OUTPUT');
const require=createRequire(resolve(analyzer,'package.json'));
const ts=require('typescript');
const original=require('node:module')._resolveFilename;
require('node:module')._resolveFilename=function(name,...args){
  return original.call(this,name.startsWith('@/')?resolve(analyzer,name.slice(2)):name,...args);
};
require.extensions['.ts']=(module,file)=>{
  const source=require('node:fs').readFileSync(file,'utf8');
  module._compile(ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020}}).outputText,file);
};
const {analyzeRepo}=require(resolve(analyzer,'src/lib/scoring.ts'));
const get=async path=>{
  const res=await fetch('https://api.github.com/'+path,{headers:{Accept:'application/vnd.github+json'}});
  if(!res.ok) throw Error(`GitHub API ${res.status}; retry later if rate limited. No credentials are stored.`);
  return res.json();
};
const repos=[];
for(let page=1;page<=10;page++){
  const items=await get(`users/${owner}/repos?per_page=100&page=${page}`); repos.push(...items); if(items.length<100)break;
}
const reports=[];
for(const metadata of repos){
  const base=`repos/${metadata.full_name}`;
  try{
    const readmeData=await get(base+'/readme');
    const readme=Buffer.from(readmeData.content,'base64').toString('utf8');
    const tree=await get(base+`/git/trees/${encodeURIComponent(metadata.default_branch)}?recursive=1`);
    const languages=await get(base+'/languages');
    const report=analyzeRepo({input:{owner,repo:metadata.name,normalizedUrl:metadata.html_url},metadata,readme,
      languages,treePaths:tree.tree.map(x=>x.path),recentCommits:[]});
    reports.push({repository:metadata.html_url,score:report.overallScore,grade:report.grade,
      checks:report.checks,suggestions:report.suggestions??report.improvementSuggestions??[],
      needs_review:report.overallScore<70,tree_truncated:Boolean(tree.truncated),
      note:'Companion analyzer heuristic, not a hiring prediction. Recent commit sample omitted; inspect activity manually.'});
  }catch(error){reports.push({repository:metadata.html_url,error:String(error),score:null});}
}
writeFileSync(output,JSON.stringify({analyzer:'repo-health-analyzer/src/lib/scoring.ts',reports},null,2));
console.log(`Saved ${reports.length} public repository reports. Discuss specific gaps with the user before proposing changes.`);
