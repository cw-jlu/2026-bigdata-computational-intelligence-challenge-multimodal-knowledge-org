import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {Workbook,SpreadsheetFile,FileBlob} from '@oai/artifact-tool';
const out=process.argv[2]??path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const specs=JSON.parse(await fs.readFile(path.join(out,'workbooks.json'),'utf8'));
for(const node of specs){
 const wb=Workbook.create(),inspections=[];const qa=path.join(out,'qa/xlsx',node.node);await fs.mkdir(qa,{recursive:true});
 for(const spec of node.sheets){
  const s=wb.worksheets.add(spec.name),nr=spec.rows.length+1,nc=spec.headers.length,end=String.fromCharCode(64+nc);const r=s.getRange(`A1:${end}${nr}`);r.values=[spec.headers,...spec.rows];r.format.font={name:'宋体',size:11,color:'#000000'};r.format.fill='#FFFFFF';r.format.wrapText=true;r.format.verticalAlignment='center';r.format.borders={preset:'all',style:'thin',color:'#D9D9D9'};r.format.rowHeight=70;
  s.getRange(`A1:${end}1`).format.font={name:'宋体',size:11,bold:true,color:'#000000'};s.getRange(`A1:${end}1`).format.rowHeight=38;s.getRange(`A1:${end}1`).format.horizontalAlignment='center';
  for(let j=1;j<=nc;j++){
   const col=String.fromCharCode(64+j),header=spec.headers[j-1];let width=spec.sample_widths[col]??14;
   if(header==='批号')width=28;
   if(['机型','舰船'].includes(header))width=26;
   if(header==='活动区域')width=24;
   if(header==='备注')width=58;
   if(['任务','任务描述'].includes(header))width=34;
   s.getRange(`${col}1:${col}${nr}`).format.columnWidth=width;s.getRange(`${col}1:${col}${nr}`).setNumberFormat('@');
   if(nr>1&&['批次','架次','艘次'].includes(header))s.getRange(`${col}2:${col}${nr}`).setNumberFormat('0');
  }
  s.freezePanes.freezeRows(1);s.freezePanes.freezeColumns(3);
  inspections.push(await wb.inspect({kind:'table',range:`'${spec.name}'!A1:${end}${nr}`,include:'values,formulas',maxChars:50000,tableMaxRows:nr,tableMaxCols:nc,tableMaxCellChars:200}));
 }
 wb.recalculate();inspections.push(await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!',options:{useRegex:true,maxResults:40},summary:'formula error scan'}));
 const file=path.join(out,'official',node.node,`${node.node}机舰活动明细.xlsx`);const output=await SpreadsheetFile.exportXlsx(wb);await output.save(file);
 try{await fs.rename(file+'.inspect.ndjson',path.join(out,'audits',node.node,'workbook_export.inspect.ndjson'));}catch(e){if(e.code!=='ENOENT')throw e;}
 for(const spec of node.sheets){
  const n=spec.rows.length+1,bands=spec.name==='飞机'?['A:H','I:P']:['A:F','G:K'];
  for(let j=0;j<bands.length;j++){
   const [a,b]=bands[j].split(':');const range=`${a}1:${b}${n}`;const img=await wb.render({sheetName:spec.name,range,scale:1.3,format:'png'});await fs.writeFile(path.join(qa,`${spec.name}_${j+1}.png`),new Uint8Array(await img.arrayBuffer()));
  }
 }
 await fs.writeFile(path.join(out,'audits',node.node,'workbook_inspection.json'),JSON.stringify(inspections,null,2));console.log(JSON.stringify({node:node.node,sheets:node.sheets.map(x=>({name:x.name,records:x.rows.length})),exported:true,rendered_all_cells:true}));
}
