// Two official sheets, typed dates/counts. No additional audit tabs/columns.
import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
const out=path.resolve(process.argv[2]);
const entry=process.env.ARTIFACT_TOOL_ENTRY || path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs');
const {Workbook,SpreadsheetFile}=await import(pathToFileURL(entry).href);
const files=(await fs.readdir(path.join(out,'payloads'))).filter(f=>f.endsWith('.json')&&!f.includes('.chart_data')).sort();
const checks=[];
for(const file of files){
 const payload=JSON.parse(await fs.readFile(path.join(out,'payloads',file),'utf8'));
 const wb=Workbook.create();
 for(const name of ['飞机','舰艇']){
  const spec=payload.xlsx[name];const sh=wb.worksheets.add(name);const last=name==='飞机'?'P':'K';
  // Excel serial + date format avoids the preview's wrapped ISO timestamp.
  const rows=spec.rows.map(r=>{const x=[...r];const [y,m,d]=x[0].split('.').map(Number);x[0]=Date.UTC(y,m-1,d)/86400000+25569;return x;});
  sh.getRange(`A1:${last}${rows.length+1}`).values=[spec.columns,...rows];
  sh.showGridLines=false;sh.freezePanes.freezeRows(1);sh.freezePanes.freezeColumns(3);
  const all=sh.getRange(`A1:${last}${rows.length+1}`);
  all.format.font={name:'Microsoft YaHei',size:10,color:'#222222'};
  all.format.verticalAlignment='center';all.format.wrapText=true;all.format.columnWidth=14;all.format.rowHeight=62;
  sh.getRange(`A1:${last}1`).format={fill:'#273F55',font:{name:'Microsoft YaHei',size:10,bold:true,color:'#FFFFFF'},rowHeight:32,wrapText:true,horizontalAlignment:'center'};
  sh.getRange(`A2:A${rows.length+1}`).format.numberFormat='yyyy-mm-dd';sh.getRange('A:A').format.columnWidth=13;
  sh.getRange(name==='飞机'?'D:D':'C:C').format.columnWidth=29;
  sh.getRange(name==='飞机'?'E:E':'D:D').format.columnWidth=24;
  sh.getRange(name==='飞机'?'M:O':'H:I').format.columnWidth=24;
  sh.getRange(name==='飞机'?'P:P':'K:K').format.columnWidth=66;
  const numCols=name==='飞机'?['F','G']:['E'];
  for(const col of numCols){sh.getRange(`${col}2:${col}${rows.length+1}`).format.numberFormat='0';sh.getRange(`${col}:${col}`).format.columnWidth=9;}
  if(rows.length)sh.tables.add(`A1:${last}${rows.length+1}`,true,name==='飞机'?'AircraftDetails':'ShipDetails');
 }
 wb.recalculate();
 checks.push({day:payload.day,inspect:(await wb.inspect({kind:'sheet,table',maxChars:2000,tableMaxRows:3,tableMaxCols:5})).ndjson,
              errors:(await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!',options:{useRegex:true,maxResults:50},maxChars:1000})).ndjson});
 const target=path.join(out,'日报',payload.day,`${payload.day}机舰活动明细.xlsx`);
 await (await SpreadsheetFile.exportXlsx(wb)).save(target);
 const qa=path.join(out,'../audit/xlsx_preview',payload.day);await fs.mkdir(qa,{recursive:true});
 // The runtime creates inspection sidecars beside exports. Keep all QA outside
 // the official submission directories, including on repeated generation.
 try{await fs.rename(target+'.inspect.ndjson',path.join(qa,'export.inspect.ndjson'));}catch(e){if(e.code!=='ENOENT')throw e;}
 for(const name of ['飞机','舰艇']){
  const r=(name==='飞机'?'A1:P':'A1:K')+Math.min(payload.xlsx[name].rows.length+1,7);
  const blob=await wb.render({sheetName:name,range:r,scale:1.3,format:'png'});
  await fs.writeFile(path.join(qa,`${name}.png`),new Uint8Array(await blob.arrayBuffer()));
 }
 console.log(payload.day+' XLSX saved and rendered');
}
await fs.writeFile(path.join(out,'../audit/workbook_inspection.json'),JSON.stringify(checks,null,2));
