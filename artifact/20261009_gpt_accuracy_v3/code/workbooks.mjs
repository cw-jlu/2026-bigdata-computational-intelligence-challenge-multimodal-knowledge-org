import fs from 'node:fs/promises';
import path from 'node:path';
import {Workbook,SpreadsheetFile} from '@oai/artifact-tool';
const [input,target,qa]=process.argv.slice(2);
await fs.mkdir(qa,{recursive:true});
const books=JSON.parse(await fs.readFile(input,'utf8'));
const inspections=[];
for(const book of books){
  const wb=Workbook.create();
    for(const data of book.sheets){
    const ws=wb.worksheets.add(data.name);ws.showGridLines=false;
    const last=data.name==='飞机'?'P':'K';
    // This runtime serializes Date objects to ISO strings. Use an actual Excel
    // date serial with a date number format, verified by the saved-file reader.
    const values=[data.headers,...data.rows.map(row=>row.map((v,i)=>i===0?Date.parse(v+'T00:00:00Z')/86400000+25569:v))];
    const range=ws.getRange(`A1:${last}${values.length}`);range.values=values;
    range.format.font={name:'Microsoft YaHei',size:10,color:'#182532'};
    range.format.wrapText=true;range.format.verticalAlignment='center';range.format.rowHeight=82;
    ws.getRange(`A1:${last}1`).format={fill:'#294C67',font:{name:'Microsoft YaHei',size:10,bold:true,color:'#FFFFFF'},rowHeight:30,horizontalAlignment:'center',verticalAlignment:'center'};
    ws.getRange(`A2:A${values.length}`).format.numberFormat='yyyy.mm.dd';
    const widths=data.name==='飞机'?[14,12,14,36,28,9,9,18,14,14,14,12,24,24,24,70]:[14,14,36,29,10,20,12,25,25,20,70];
    for(let i=0;i<widths.length;i++)ws.getRangeByIndexes(0,i,values.length,1).format.columnWidth=widths[i];
    for(const col of (data.name==='飞机'?['F','G']:['E'])){
      ws.getRange(`${col}2:${col}${values.length}`).setNumberFormat('0');
      ws.getRange(`${col}2:${col}${values.length}`).format.horizontalAlignment='right';
    }
    ws.freezePanes.freezeRows(1);ws.freezePanes.freezeColumns(3);
    if(values.length>1)ws.tables.add(`A1:${last}${values.length}`,true,data.name==='飞机'?'AircraftActivities':'ShipActivities');
    ws.getRange(`A2:A${values.length}`).format.numberFormat='yyyy.mm.dd';
  }
  wb.recalculate();
  const check=await wb.inspect({kind:'workbook,sheet,table',tableMaxRows:3,tableMaxCols:5,maxChars:5000});
  const errors=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!|#SPILL!',options:{useRegex:true,maxResults:100},maxChars:2000});
  inspections.push({date:book.date,summary:check.ndjson,errors:errors.ndjson});
  for(const data of book.sheets){
    const last=data.name==='飞机'?'P':'K';
    const preview=await wb.render({sheetName:data.name,range:`A1:${last}${data.rows.length+1}`,scale:1.1,format:'png'});
    await fs.writeFile(path.join(qa,`${book.date}_${data.name}.png`),new Uint8Array(await preview.arrayBuffer()));
  }
  const output=await SpreadsheetFile.exportXlsx(wb);
  const saved=path.join(target,book.date,book.date+'机舰活动明细.xlsx');
  await output.save(saved);
  try{await fs.rename(saved+'.inspect.ndjson',path.join(qa,book.date+'_export_inspect.ndjson'));}catch(e){if(e.code!=='ENOENT')throw e;}
  console.log('XLSX saved',book.date);
}
await fs.writeFile(path.join(qa,'workbook_inspections.json'),JSON.stringify(inspections,null,2));
