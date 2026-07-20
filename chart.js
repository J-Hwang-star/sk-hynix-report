
const dates = ["2026-04-16", "2026-04-17", "2026-04-20", "2026-04-21", "2026-04-22", "2026-04-23", "2026-04-24", "2026-04-27", "2026-04-28", "2026-04-29", "2026-04-30", "2026-05-04", "2026-05-06", "2026-05-07", "2026-05-08", "2026-05-11", "2026-05-12", "2026-05-13", "2026-05-14", "2026-05-15", "2026-05-18", "2026-05-19", "2026-05-20", "2026-05-21", "2026-05-22", "2026-05-26", "2026-05-27", "2026-05-28", "2026-05-29", "2026-06-01", "2026-06-02", "2026-06-04", "2026-06-05", "2026-06-08", "2026-06-09", "2026-06-10", "2026-06-11", "2026-06-12", "2026-06-15", "2026-06-16", "2026-06-17", "2026-06-18", "2026-06-19", "2026-06-22", "2026-06-23", "2026-06-24", "2026-06-25", "2026-06-26", "2026-06-29", "2026-06-30", "2026-07-01", "2026-07-02", "2026-07-03", "2026-07-06", "2026-07-07", "2026-07-08", "2026-07-09", "2026-07-10", "2026-07-13", "2026-07-14", "2026-07-15", "2026-07-16", "2026-07-20"];
const closes = [1155000.0, 1128000.0, 1166000.0, 1224000.0, 1223000.0, 1225000.0, 1222000.0, 1292000.0, 1300000.0, 1293000.0, 1286000.0, 1447000.0, 1601000.0, 1654000.0, 1686000.0, 1880000.0, 1835000.0, 1976000.0, 1970000.0, 1819000.0, 1840000.0, 1745000.0, 1745000.0, 1940000.0, 1941000.0, 2052000.0, 2243000.0, 2289000.0, 2333000.0, 2363000.0, 2360000.0, 2298000.0, 2070000.0, 1911000.0, 2215000.0, 2048000.0, 2101000.0, 2150000.0, 2288000.0, 2382000.0, 2521000.0, 2685000.0, 2764000.0, 2919000.0, 2555000.0, 2621000.0, 2917000.0, 2673000.0, 2628000.0, 2650000.0, 2560000.0, 2187000.0, 2425000.0, 2343000.0, 2201000.0, 2076000.0, 2186000.0, 2180000.0, 1845000.0, 1913000.0, 2082000.0, 1842000.0, 1764000.0];
const ma20 = [null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, 1469100.0, 1503350.0, 1534200.0, 1563150.0, 1598950.0, 1634850.0, 1676200.0, 1727250.0, 1777100.0, 1828750.0, 1882250.0, 1935950.0, 1978500.0, 2001950.0, 2014800.0, 2041250.0, 2049650.0, 2062950.0, 2071650.0, 2087550.0, 2115700.0, 2149750.0, 2196750.0, 2247700.0, 2296650.0, 2327350.0, 2355800.0, 2389500.0, 2408700.0, 2423450.0, 2437800.0, 2447800.0, 2442250.0, 2460000.0, 2481600.0, 2480900.0, 2482300.0, 2486550.0, 2488050.0, 2465900.0, 2442450.0, 2420500.0, 2378350.0, 2328350.0];
const ma60 = [null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, 2009083.0, 2024533.0, 2036433.0, 2046400.0];
const volumes = [2901319, 3578235, 3748014, 3516960, 2894919, 5343871, 3127857, 4563073, 3002713, 3001208, 3342342, 5776641, 6631934, 5860618, 4278087, 7433039, 9160593, 7126921, 6040068, 7485233, 6481608, 4575855, 5535123, 5096690, 3135190, 4903591, 7545783, 6229499, 8518013, 5602897, 5837216, 3941067, 5778751, 6610833, 5878039, 151, 6625775, 5286416, 3872910, 3644469, 3980010, 5808765, 7478195, 5179795, 8050335, 7487916, 6790853, 7467492, 5217788, 5109213, 4277276, 7685914, 7984914, 4235360, 6351195, 6975631, 6261504, 4827239, 8040043, 10447011, 6046951, 5608812, 6302600];
const bbUpper = [null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, 2068183.0, 2105141.0, 2117962.0, 2127121.0, 2163174.0, 2189646.0, 2225627.0, 2288588.0, 2352590.0, 2409347.0, 2452078.0, 2470523.0, 2483881.0, 2476140.0, 2462476.0, 2469206.0, 2470820.0, 2472211.0, 2480526.0, 2504436.0, 2532266.0, 2582447.0, 2648138.0, 2714174.0, 2828110.0, 2843009.0, 2870278.0, 2958298.0, 2989022.0, 3010626.0, 3032732.0, 3043949.0, 3046285.0, 3038292.0, 3003027.0, 3003870.0, 3000518.0, 2992859.0, 2990323.0, 3039348.0, 3066471.0, 3063483.0, 3057816.0, 3034958.0];
const bbLower = [null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, 870017.0, 901559.0, 950438.0, 999179.0, 1034726.0, 1080054.0, 1126773.0, 1165912.0, 1201610.0, 1248153.0, 1312422.0, 1401377.0, 1473119.0, 1527760.0, 1567124.0, 1613294.0, 1628480.0, 1653689.0, 1662774.0, 1670664.0, 1699134.0, 1717053.0, 1745362.0, 1781226.0, 1765190.0, 1811691.0, 1841322.0, 1820702.0, 1828378.0, 1836274.0, 1842868.0, 1851651.0, 1838215.0, 1881708.0, 1960173.0, 1957930.0, 1964082.0, 1980241.0, 1985777.0, 1892452.0, 1818429.0, 1777517.0, 1698884.0, 1621742.0];
const macdLine = [0.0, -2154.0, -785.0, 4922.0, 9258.0, 12710.0, 15030.0, 22260.0, 28309.0, 32168.0, 34266.0, 48362.0, 71140.0, 92403.0, 110562.0, 139005.0, 156116.0, 178990.0, 194393.0, 192200.0, 189967.0, 178474.0, 167436.0, 172435.0, 174467.0, 182925.0, 202703.0, 219559.0, 233773.0, 244638.0, 250123.0, 246625.0, 222885.0, 189062.0, 184658.0, 165782.0, 153332.0, 145738.0, 149137.0, 157599.0, 173521.0, 197100.0, 219630.0, 247144.0, 236846.0, 231344.0, 248010.0, 238776.0, 225231.0, 213807.0, 195240.0, 148714.0, 129553.0, 106523.0, 75937.0, 41138.0, 22179.0, 6594.0, -32415.0, -57184.0, -62456.0, -85021.0, -107953.0];
const macdSignal = [0.0, -431.0, -502.0, 583.0, 2318.0, 4396.0, 6523.0, 9670.0, 13398.0, 17152.0, 20575.0, 26132.0, 35134.0, 46588.0, 59383.0, 75307.0, 91469.0, 108973.0, 126057.0, 139286.0, 149422.0, 155233.0, 157673.0, 160626.0, 163394.0, 167300.0, 174381.0, 183416.0, 193488.0, 203718.0, 212999.0, 219724.0, 220356.0, 214097.0, 208210.0, 199724.0, 190446.0, 181504.0, 175031.0, 171544.0, 171940.0, 176972.0, 185504.0, 197832.0, 205634.0, 210776.0, 218223.0, 222334.0, 222913.0, 221092.0, 215922.0, 202480.0, 187895.0, 171620.0, 152484.0, 130214.0, 108607.0, 88205.0, 64081.0, 39828.0, 19371.0, -1507.0, -22796.0];
const macdHist = [0.0, -1723.0, -284.0, 4339.0, 6940.0, 8313.0, 8506.0, 12589.0, 14911.0, 15015.0, 13691.0, 22230.0, 36006.0, 45816.0, 51180.0, 63698.0, 64647.0, 70017.0, 68336.0, 52915.0, 40545.0, 23242.0, 9763.0, 11810.0, 11073.0, 15625.0, 28323.0, 36143.0, 40285.0, 40920.0, 37125.0, 26901.0, 2529.0, -25035.0, -23551.0, -33942.0, -37114.0, -35766.0, -25894.0, -13946.0, 1581.0, 20129.0, 34127.0, 49312.0, 31212.0, 20568.0, 29787.0, 16442.0, 2318.0, -7285.0, -20681.0, -53766.0, -58342.0, -65098.0, -76546.0, -89077.0, -86428.0, -81610.0, -96496.0, -97012.0, -81827.0, -83514.0, -85157.0];
const atrData = [31000.0, 34000.0, 47000.0, 62000.0, 38000.0, 84000.0, 49000.0, 95000.0, 36000.0, 36000.0, 39000.0, 164000.0, 167000.0, 98000.0, 98000.0, 263000.0, 163000.0, 209000.0, 57000.0, 206000.0, 166000.0, 100000.0, 88000.0, 209000.0, 40000.0, 146000.0, 306000.0, 154000.0, 90000.0, 102000.0, 148000.0, 98000.0, 228000.0, 217000.0, 315000.0, 223000.0, 203000.0, 203000.0, 172000.0, 114000.0, 189000.0, 217000.0, 206000.0, 217000.0, 407000.0, 250000.0, 366000.0, 317000.0, 171000.0, 201000.0, 221000.0, 373000.0, 409000.0, 205000.0, 263000.0, 253000.0, 194000.0, 139000.0, 341000.0, 258000.0, 258000.0, 261000.0, 157000.0];
const adxData = [null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, 64.8, 61.3, 57.9, 53.3, 48.9, 45.2, 39.9, 36.4, 34.6, 33.1, 32.2, 30.4, 28.6, 26.6, 23.4, 22.2, 21.2, 21.2, 20.4, 19.0, 21.0, 23.8, 24.6, 25.7, 26.6, 25.6, 24.3, 23.3, 24.3, 24.9, 26.1, 27.4, 29.8, 32.8, 34.2, 35.3, 37.4];
const kData = [null, null, null, null, null, null, null, null, null, null, null, null, null, 118.2, 113.2, 77.1, 74.1, 72.0, 71.6, 71.2, 69.0, 67.6, 67.6, 67.4, 65.1, 39.1, 24.9, 22.6, 10.7, 10.5, 10.3, 10.3, 10.3, 10.3, 10.3, 10.3, -5.2, -16.5, -16.5, -16.5, -13.6, -10.3, -8.8, -8.3, -8.3, -8.3, -8.0, -19.1, -19.1, -19.1, -46.1, -52.9, -29.8, -29.8, -29.8, -29.8, -29.8, -29.8, -6.5, 6.6, 7.2, 8.1, 8.1];
const dData = [null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, 102.8, 88.1, 74.4, 72.6, 71.6, 70.6, 69.3, 68.1, 67.6, 66.7, 57.2, 43.0, 28.8, 19.4, 14.6, 10.5, 10.4, 10.3, 10.3, 10.3, 10.3, 5.1, -3.8, -12.7, -16.5, -15.5, -13.5, -10.9, -9.1, -8.5, -8.3, -8.2, -11.8, -15.4, -19.1, -28.1, -39.4, -42.9, -37.5, -29.8, -29.8, -29.8, -29.8, -22.1, -9.9, 2.4, 7.3, 7.8];
const jData = [null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, 25.6, 46.0, 67.2, 69.8, 70.4, 65.9, 64.4, 66.7, 67.1, 61.9, 2.8, -11.3, 10.0, -6.6, 2.2, 10.0, 10.2, 10.3, 10.3, 10.3, 10.3, -26.0, -41.9, -24.0, -16.5, -9.8, -4.0, -4.5, -6.8, -8.1, -8.3, -7.6, -33.6, -26.4, -19.1, -82.2, -79.9, -3.6, -14.5, -29.8, -29.8, -29.8, -29.8, 24.5, 39.6, 16.7, 9.7, 8.7];
const volMa20 = [null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, 4940682.0, 5119697.0, 5169578.0, 5258933.0, 5337920.0, 5349933.0, 5327919.0, 5548816.0, 5632137.0, 5907902.0, 6037986.0, 6162730.0, 6070951.0, 6028292.0, 6065803.0, 6145800.0, 5774156.0, 5647415.0, 5555390.0, 5447032.0, 5254994.0, 5129914.0, 5191559.0, 5288713.0, 5292868.0, 5538626.0, 5667842.0, 5630095.0, 5691995.0, 5526984.0, 5502299.0, 5424302.0, 5611545.0, 5721853.0, 5603079.0, 5626737.0, 5975511.0, 5957298.0, 5934339.0, 6142695.0, 6482822.0, 6586170.0, 6576172.0, 6517392.0];
const MONTHS = 3;

// ===== Canvas API chart drawing (no Chart.js) =====
function canvas(elId) { return document.getElementById(elId); }
function ctx(elId) { const c=canvas(elId); c.width=c.parentElement.clientWidth-40; c.height=300; return c.getContext('2d'); }
function drawLine(data, color, width, dash, ctx2, w, h, min, range) {
  if(range==0) range=1;
  const norm = v => v==null ? null : (v-min)/range;
  ctx2.strokeStyle=color; ctx2.lineWidth=width; ctx2.setLineDash(dash||[]); ctx2.beginPath();
  let started=false;
  for(let i=0;i<data.length;i++) { if(data[i]==null) continue; const x=10+(i/(data.length-1))*(w-20); const y=h-10-norm(data[i])*(h-20); if(y<h+10&&y>10){if(!started){ctx2.moveTo(x,y);started=true}else{ctx2.lineTo(x,y)}} }
  ctx2.stroke(); ctx2.setLineDash([]);
}
function drawPriceChart() {
  const c=ctx('priceChart'), w=c.width, h=c.height, d=closes;
  const max=Math.max(...d.filter(v=>v)), min=Math.min(...d.filter(v=>v)), range=max-min||1;
  c.strokeStyle='#334155'; c.lineWidth=0.5;
  for(let i=0;i<=4;i++) { const y=10+(i/4)*(h-20); c.beginPath(); c.moveTo(10,y); c.lineTo(w-10,y); c.stroke();
    c.fillStyle='#64748b'; c.font='10px sans-serif'; c.fillText(Math.round(max-(i/4)*range),2,y-2); }
  // BB upper/lower band fill
  c.fillStyle='rgba(148,163,184,0.08)'; c.beginPath(); let s=false;
  for(let i=0;i<bbUpper.length;i++) { if(bbUpper[i]==null) continue; const x=10+(i/(bbUpper.length-1))*(w-20); const y=h-10-(bbUpper[i]-min)/(range)*(h-20); if(!s){c.moveTo(x,y);s=true}else{c.lineTo(x,y)} }
  for(let i=bbLower.length-1;i>=0;i--) { if(bbLower[i]==null) continue; const x=10+(i/(bbLower.length-1))*(w-20); const y=h-10-(bbLower[i]-min)/(range)*(h-20); c.lineTo(x,y); }
  c.closePath(); c.fill();
  drawLine(bbUpper,'rgba(148,163,184,0.4)',1,[],c,w,h,min,range); drawLine(bbLower,'rgba(148,163,184,0.4)',1,[],c,w,h,min,range);
  drawLine(closes,'#38bdf8',2,[],c,w,h,min,range); drawLine(ma20,'#f59e0b',1.5,[5,5],c,w,h,min,range); drawLine(ma60,'#a78bfa',1.5,[5,5],c,w,h,min,range);
  // Legend
  c.font='11px sans-serif'; let lx=w-150;
  c.fillStyle='#38bdf8'; c.fillRect(lx,4,12,3); c.fillStyle='#e2e8f0'; c.fillText('??',lx+16,8);
  c.fillStyle='#f59e0b'; c.fillRect(lx+60,4,12,3); c.fillText('MA20',lx+74,8);
  c.fillStyle='#a78bfa'; c.fillRect(lx+110,4,12,3); c.fillText('MA60',lx+124,8);
}
function drawVolChart() {
  const c=ctx('volChart'), w=c.width, h=c.height;
  const max=Math.max(...volumes);
  c.fillStyle='#334155'; c.strokeStyle='#334155'; c.lineWidth=0.5;
  for(let i=0;i<=4;i++) { const y=10+(i/4)*(h-20); c.beginPath(); c.moveTo(10,y); c.lineTo(w-10,y); c.stroke();
    c.fillStyle='#64748b'; c.font='10px sans-serif'; c.fillText(Math.round(max*(1-i/4)/1000)+'K',2,y-2); }
  const barW=Math.max(2,(w-20)/volumes.length-2);
  for(let i=0;i<volumes.length;i++) { const bh=(volumes[i]/max)*(h-20); const x=10+i*(w-20)/volumes.length+1; c.fillStyle='#3b82f680'; c.fillRect(x,h-10-bh,barW,bh); }
}
function drawMACDChart() {
  const c=ctx('macdChart'), w=c.width, h=c.height, d=macdHist;
  const max=Math.max(...macdLine.filter(v=>v),...macdSignal.filter(v=>v),...macdHist.filter(v=>v),0);
  const min=Math.min(...macdLine.filter(v=>v),...macdSignal.filter(v=>v),...macdHist.filter(v=>v),0);
  const range=max-min||1;
  // Zero line
  const zeroY=h-10-(0-min)/(range)*(h-20); c.strokeStyle='#475569'; c.lineWidth=1; c.setLineDash([3,3]); c.beginPath(); c.moveTo(10,zeroY); c.lineTo(w-10,zeroY); c.stroke(); c.setLineDash([]);
  // Histogram
  const barW=Math.max(2,(w-20)/macdHist.length-2);
  for(let i=0;i<macdHist.length;i++) { if(macdHist[i]==null) continue; const bh=Math.abs(macdHist[i]/range)*(h-20); const y=macdHist[i]>=0?zeroY-bh:zeroY; c.fillStyle=macdHist[i]>=0?'rgba(39,174,96,0.6)':'rgba(231,76,60,0.6)'; c.fillRect(10+i*(w-20)/macdHist.length+1,y,barW,bh); }
  drawLine(macdLine,'#38bdf8',1.5,[],c,w,h,min,range); drawLine(macdSignal,'#f59e0b',1.5,[5,5],c,w,h,min,range);
}
function drawATRADXChart() {
  const c=ctx('atrAdxChart'), w=c.width, h=c.height;
  const atrMax=Math.max(...atrData.filter(v=>v)), adxMax=Math.max(...adxData.filter(v=>v),1);
  // Y axis left (ATR)
  c.strokeStyle='#334155'; c.lineWidth=0.5;
  for(let i=0;i<=4;i++) { const y=10+(i/4)*(h-20); c.beginPath(); c.moveTo(10,y); c.lineTo(w-10,y); c.stroke();
    c.fillStyle='#e67e22'; c.font='10px sans-serif'; c.fillText(Math.round(atrMax*(1-i/4)),2,y-2); }
  // Y axis right (ADX)
  c.fillStyle='#e74c3c'; c.textAlign='right';
  for(let i=0;i<=4;i++) { const y=10+(i/4)*(h-20); c.fillText(Math.round(adxMax*i/4),w-2,y-2); }
  c.textAlign='left';
  const atrMin=Math.min(...atrData.filter(v=>v)), adxMin=Math.min(...adxData.filter(v=>v),0);
  drawLine(atrData,'#e67e22',1.5,[],c,w,h,atrMin,atrMin==atrMax?1:atrMax-atrMin);
  drawLine(adxData,'#e74c3c',1.5,[],c,w,h,adxMin,adxMin==adxMax?1:adxMax-adxMin);
}
function drawKDJChart() {
  const c=ctx('kdjChart'), w=c.width, h=c.height;
  c.strokeStyle='#334155'; c.lineWidth=0.5;
  for(var fi=0;fi<[0,25,50,75,100].length;fi++){const v=[0,25,50,75,100][fi];const y=h-10-(v/100)*(h-20);c.beginPath();c.moveTo(10,y);c.lineTo(w-10,y);c.stroke();c.fillStyle='#64748b';c.font='10px sans-serif';c.fillText(v+'',2,y-2);}
  drawLine(kData,'#38bdf8',1.5,[],c,w,h,0,100); drawLine(dData,'#f59e0b',1.5,[],c,w,h,0,100); drawLine(jData,'#a78bfa',1.5,[],c,w,h,0,100);
}
function drawVolMaChart() {
  const c=ctx('volMaChart'), w=c.width, h=c.height;
  const max=Math.max(...volumes,...volMa20.filter(v=>v));
  c.fillStyle='#334155'; c.strokeStyle='#334155'; c.lineWidth=0.5;
  for(let i=0;i<=4;i++) { const y=10+(i/4)*(h-20); c.beginPath(); c.moveTo(10,y); c.lineTo(w-10,y); c.stroke();
    c.fillStyle='#64748b'; c.font='10px sans-serif'; c.fillText(Math.round(max*(1-i/4)/1000)+'K',2,y-2); }
  const barW=Math.max(2,(w-20)/volumes.length-2);
  for(let i=0;i<volumes.length;i++) { const bh=(volumes[i]/max)*(h-20); const x=10+i*(w-20)/volumes.length+1; c.fillStyle='#3b82f680'; c.fillRect(x,h-10-bh,barW,bh); }
  drawLine(volMa20,'#f59e0b',1.5,[5,5],c,w,h);
}
window.onload=function(){ drawPriceChart(); drawVolChart(); drawMACDChart(); drawATRADXChart(); drawKDJChart(); drawVolMaChart(); };
window.addEventListener('resize',function(){ drawPriceChart(); drawVolChart(); drawMACDChart(); drawATRADXChart(); drawKDJChart(); drawVolMaChart(); });

// =====   =====
const TICKER = "000660.KS";
let toastTimer = null;

function showToast(msg, isError) {
  let t = document.getElementById('toast');
  if (!t) {
    t = document.createElement('div');
    t.id = 'toast';
    t.className = 'toast';
    document.body.appendChild(t);
  }
  t.textContent = msg;
  t.className = 'toast show' + (isError ? ' error' : '');
  if (toastTimer) clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.className = 'toast' + (isError ? ' error' : ''), 2200);
}

//  
function sma(arr, n) {
  const out = new Array(arr.length).fill(null);
  for (let i = n - 1; i < arr.length; i++) {
    let sum = 0;
    for (let j = i - n + 1; j <= i; j++) sum += arr[j];
    out[i] = sum / n;
  }
  return out;
}

// RSI(14) 
function calcRSI(arr, n = 14) {
  const out = new Array(arr.length).fill(null);
  let gain = 0, loss = 0;
  for (let i = 1; i <= n; i++) {
    const d = arr[i] - arr[i - 1];
    if (d >= 0) gain += d; else loss -= d;
  }
  let avgG = gain / n, avgL = loss / n;
  out[n] = 100 - 100 / (1 + (avgL === 0 ? 100 : avgG / avgL));
  for (let i = n + 1; i < arr.length; i++) {
    const d = arr[i] - arr[i - 1];
    const g = d > 0 ? d : 0, l = d < 0 ? -d : 0;
    avgG = (avgG * (n - 1) + g) / n;
    avgL = (avgL * (n - 1) + l) / n;
    out[i] = avgL === 0 ? 100 : 100 - 100 / (1 + avgG / avgL);
  }
  return out;
}

//  
function std(arr, n, end) {
  const slice = arr.slice(end - n + 1, end + 1);
  const mean = slice.reduce((a, b) => a + b, 0) / n;
  const variance = slice.reduce((a, b) => a + (b - mean) ** 2, 0) / n;
  return Math.sqrt(variance);
}

//   
function calcBB(closes, n = 20, k = 2) {
  const upper = new Array(closes.length).fill(null);
  const lower = new Array(closes.length).fill(null);
  const width = new Array(closes.length).fill(null);
  for (let i = n - 1; i < closes.length; i++) {
    const ma = sma(closes.slice(), n)[i];
    if (ma == null) continue;
    const sd = std(closes, n, i);
    upper[i] = ma + k * sd;
    lower[i] = ma - k * sd;
    width[i] = ma > 0 ? (upper[i] - lower[i]) / ma * 100 : 0;
  }
  return { upper, lower, width };
}

// EMA 
function ema(arr, n) {
  const out = new Array(arr.length).fill(null);
  const k = 2 / (n + 1);
  let prev = null;
  for (let i = 0; i < arr.length; i++) {
    if (arr[i] == null) continue;
    if (prev == null) prev = arr[i];
    else prev = arr[i] * k + prev * (1 - k);
    out[i] = prev;
  }
  return out;
}

// MACD  (12, 26, 9)
function calcMACD(closes) {
  const ema12 = ema(closes, 12);
  const ema26 = ema(closes, 26);
  const macd = closes.map((_, i) =>
    (ema12[i] != null && ema26[i] != null) ? ema12[i] - ema26[i] : null);
  const signal = ema(macd.map(v => v == null ? 0 : v), 9).map((v, i) => macd[i] == null ? null : v);
  const hist = macd.map((v, i) => (v != null && signal[i] != null) ? v - signal[i] : null);
  return { macd, signal, hist };
}

// =====    (JS) =====
const POSITIVE_WORDS = ["\uc0c1\uc2b9", "\uae09\ub4f1", "\uc624\ub984", "\uae0d\uc815", "\ud638\uc870", "\uc2e0\uace0\uac00", "\ucd5c\uace0", "\ucd5c\ub300", "\uc99d\uac00", "\uc131\uc7a5", "\uac1c\uc120", "\ud68c\ubcf5", "\uc218\uc775", "\uc774\uc775", "\ud751\uc790", "\uc2e4\uc801", "\uac1c\ud601", "\uae30\ub300", "\ud601\uc2e0", "\ub3cc\ud30c", "\uac15\uc138", "\uc0c1\ud5a5", "\ubaa9\ud45c\uac00", "\ub9e4\uc218", "\ucd94\ucc9c", "\ub300\ub7c9", "\uc218\uc8fc", "\uacc4\uc57d", "\ud22c\uc790", "\ud655\ub300", "\uc810\uc720\uc728", "\uc99d\uc0b0", "\ud611\ub825", "\uc131\uacf5", "\uc644\uc131", "\uc548\uc815", "\uac1c\ub9c9", "\uae30\ub300\uac10", "\ubc18\ub4f1", "\uae09\uc0c1\uc2b9", "\uc0ac\uc0c1\ucd5c\uace0", "\uc0ac\uc0c1 \ucd5c\uace0", "\uc0ac\uc918"];
const NEGATIVE_WORDS = ["\ud558\ub77d", "\uae09\ub77d", "\ub0b4\ub9bc", "\ubd80\uc815", "\uc801\uc790", "\uac10\uc18c", "\ubd80\uc9c4", "\uc6b0\ub824", "\ub9ac\uc2a4\ud06c", "\ud558\ud5a5", "\uc190\uc2e4", "\uc704\uae30", "\ucda9\uaca9", "\uc57d\uc138", "\ud3ed\ub77d", "\uae09\uac10", "\ud558\ud68c", "\ubbf8\ub2ec", "\uc9c0\uc5f0", "\uc5f0\uae30", "\ucde8\uc18c", "\uc911\ub2e8", "\uc911\uc9c0", "\ubb38\uc81c", "\uc0ac\uace0", "\uc18c\uc1a1", "\ubc8c\uae08", "\uc81c\uc7ac", "\uc870\uc0ac", "\uc545\ud654", "\ud558\ub77d\uc138", "\uc57d\ud654", "\ucde8\uc57d", "\uacbd\uace0", "\ud558\ud5a5\uc870\uc815", "\ubaa9\ud45c\uac00 \ud558\ud5a5", "\uc190\uc2e4", "\uc801\uc804", "\uae00\ub85c\ubc8c", "\uacf5\uae09\uacfc\uc789", "\uc7ac\uace0"];

function classifySentiment(text) {
  if (!text) return 0;
  let pos = 0, neg = 0;
  for (const w of POSITIVE_WORDS) if (text.includes(w)) pos++;
  for (const w of NEGATIVE_WORDS) if (text.includes(w)) neg++;
  return pos > neg ? 1 : neg > pos ? -1 : 0;
}

function analyzeSentimentJS(news) {
  let p = 0, n = 0, u = 0;
  for (const item of news) {
    const s = classifySentiment((item.title || '') + ' ' + (item.desc || ''));
    item.sentiment = s;
    if (s > 0) p++; else if (s < 0) n++; else u++;
  }
  return { score: p - n, pos: p, neg: n, neu: u };
}

// Google News RSS  
async function fetchNews() {
  const rssUrl = 'https://news.google.com/rss/search?q=' + encodeURIComponent('SK ????????????') + '&hl=ko&gl=KR&ceid=KR:ko';
  const proxies = [
    `https://corsproxy.io/?url=${encodeURIComponent(rssUrl)}`,
    `https://api.allorigins.win/raw?url=${encodeURIComponent(rssUrl)}`,
  ];
  let lastErr;
  for (const url of proxies) {
    try {
      const r = await fetch(url);
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const text = await r.text();
      const parser = new DOMParser();
      const xml = parser.parseFromString(text, 'text/xml');
      const items = [...xml.querySelectorAll('item')].slice(0, 5).map(it => {
        let title = it.querySelector('title')?.textContent || '';
        let source = '';
        const dashIdx = title.lastIndexOf(' - ');
        if (dashIdx > 0) { source = title.slice(dashIdx + 3); title = title.slice(0, dashIdx); }
        let pub = it.querySelector('pubDate')?.textContent || '';
        try {
          const d = new Date(pub);
          if (!isNaN(d)) pub = d.toISOString().slice(0, 16).replace('T', ' ');
        } catch (e) {}
        return {
          title, source,
          link: it.querySelector('link')?.textContent || '',
          pubDate: pub,
          desc: source ? `??: ${source}` : '',
        };
      });
      return items;
    } catch (e) { lastErr = e; }
  }
  throw lastErr || new Error('?? ?? ??');
}

//    (Python  )
function calcSignal(cur, ma20v, ma60v, rsi, pos, bbPos, bbWidth, macdV, macdSigV, macdHistV, macdTrend, sentScore) {
  let score = 0;
  const reasons = [];
  if (ma20v != null && ma60v != null) {
    if (ma20v > ma60v) { score += 1; reasons.push("MA20 > MA60 (golden cross) - Bullish"); }
    else { score -= 1; reasons.push("MA20 < MA60 (death cross) - Bearish"); }
  }
  if (ma20v != null) {
    if (cur > ma20v) { score += 1; reasons.push(`Price ${Math.round(cur)} above MA20 ${Math.round(ma20v)} - Bullish`); }
    else { score -= 1; reasons.push(`Price ${Math.round(cur)} below MA20 ${Math.round(ma20v)} - Bearish`); }
  }
  if (rsi != null) {
    if (rsi < 30) { score += 2; reasons.push(`RSI ${rsi.toFixed(1)} - Oversold (buy signal)`); }
    else if (rsi > 70) { score -= 2; reasons.push(`RSI ${rsi.toFixed(1)} - Overbought (sell signal)`); }
    else { reasons.push(`RSI ${rsi.toFixed(1)} - Neutral`); }
  }
  if (pos > 80) { score -= 1; reasons.push(`Price near high of range (${Math.round(pos)}%) - Bearish`); }
  else if (pos < 20) { score += 1; reasons.push(`Price near low of range (${Math.round(pos)}%) - Bullish`); }
  if (bbPos != null) {
    if (bbPos < 10) { score += 2; reasons.push(`Price below BB lower band (at ${Math.round(bbPos)}%) - Oversold/Bounce likely`); }
    else if (bbPos > 90) { score -= 2; reasons.push(`Price above BB upper band (at ${Math.round(bbPos)}%) - Overbought/Reversal likely`); }
    else if (bbPos < 20) { score += 1; reasons.push(`Price in lower BB (at ${Math.round(bbPos)}%) - Bullish`); }
    else if (bbPos > 80) { score -= 1; reasons.push(`Price in upper BB (at ${Math.round(bbPos)}%) - Bearish`); }
    else { reasons.push(`Price in middle of BB (at ${Math.round(bbPos)}%) - Neutral`); }
    if (bbWidth != null) {
      if (bbWidth < 5) reasons.push(`BB width ${bbWidth.toFixed(1)}% - Squeeze (volatility expansion expected)`);
      else if (bbWidth > 20) reasons.push(`BB width ${bbWidth.toFixed(1)}% - Wide (high volatility)`);
    }
  }
  if (macdV != null && macdSigV != null) {
    if (macdV > macdSigV && macdHistV > 0) {
      if (macdTrend < 0) { score += 2; reasons.push(`MACD bullish crossover (histogram ${macdHistV >= 0 ? '+' : ''}${macdHistV.toFixed(0)}) - Strong buy signal`); }
      else { score += 1; reasons.push(`MACD bullish (histogram ${macdHistV >= 0 ? '+' : ''}${macdHistV.toFixed(0)}) - Bullish`); }
    } else if (macdV < macdSigV && macdHistV < 0) {
      if (macdTrend > 0) { score -= 2; reasons.push(`MACD bearish crossover (histogram ${macdHistV >= 0 ? '+' : ''}${macdHistV.toFixed(0)}) - Strong sell signal`); }
      else { score -= 1; reasons.push(`MACD bearish (histogram ${macdHistV >= 0 ? '+' : ''}${macdHistV.toFixed(0)}) - Bearish`); }
    } else {
      reasons.push(`MACD neutral (histogram ${macdHistV >= 0 ? '+' : ''}${macdHistV.toFixed(0)}) - No clear signal`);
    }
  }
  if (sentScore != null) {
    if (sentScore >= 2) { score += 2; reasons.push(`News sentiment ${sentScore >= 0 ? '+' : ''}${sentScore} - Strongly positive`); }
    else if (sentScore == 1) { score += 1; reasons.push(`News sentiment +1 - Positive`); }
    else if (sentScore <= -2) { score -= 2; reasons.push(`News sentiment ${sentScore} - Strongly negative`); }
    else if (sentScore == -1) { score -= 1; reasons.push(`News sentiment -1 - Negative`); }
    else { reasons.push(`News sentiment 0 - Neutral`); }
  }
  let action, label;
  if (score >= 2) { action = "BUY"; label = "Strong Buy"; }
  else if (score <= -2) { action = "SELL"; label = "Strong Sell"; }
  else { action = "HOLD"; label = "Hold (Neutral)"; }
  return { action, label, score, reasons };
}

async function fetchStockData() {
  const now = Math.floor(Date.now() / 1000);
  const start = now - (MONTHS * 30 + 5) * 86400;
  const yahooUrl = `https://query1.finance.yahoo.com/v8/finance/chart/${TICKER}?period1=${start}&period2=${now}&interval=1d`;
  // Yahoo Finance API CORS    CORS  
  const proxies = [
    `https://corsproxy.io/?url=${encodeURIComponent(yahooUrl)}`,
    `https://api.allorigins.win/raw?url=${encodeURIComponent(yahooUrl)}`,
  ];
  let lastErr;
  for (const url of proxies) {
    try {
      const r = await fetch(url);
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const data = await r.json();
      const res = data?.chart?.result?.[0];
      if (!res) throw new Error("??? ??");
      const ts = res.timestamp;
      const q = res.indicators.quote[0];
      const rows = [];
      for (let i = 0; i < ts.length; i++) {
        if (q.close[i] == null) continue;
        rows.push({
          date: new Date(ts[i] * 1000).toISOString().slice(0, 10),
          close: q.close[i],
          volume: q.volume[i] ?? 0,
        });
      }
      return rows;
    } catch (e) {
      lastErr = e;
    }
  }
  throw lastErr || new Error("?? ??? ?? ??");
}

async function refreshData() {
  const btn = document.getElementById('refreshBtn');
  if (btn.disabled) return;
  btn.disabled = true;
  btn.classList.add('loading');
  try {
    // parallel fetch stock + news
    const [rows, newsItems] = await Promise.all([
      fetchStockData(),
      fetchNews().catch(e => { console.warn('News update fail:', e); return null; }),
    ]);
    if (rows.length === 0) throw new Error("No stock data");

    // update data + news
    let sentScore = null;
    if (newsItems && newsItems.length > 0) {
      const sent = analyzeSentimentJS(newsItems);
      sentScore = sent.score;
      const newsList = document.getElementById('newsList');
      if (newsList) {
        newsList.innerHTML = newsItems.map((n, i) => {
          const badge = n.sentiment > 0 ? '<span class="badge pos">Pos</span>'
            : n.sentiment < 0 ? '<span class="badge neg">Neg</span>'
            : '<span class="badge neu">Neu</span>';
          return `<div class="news-card"><div class="news-num">${i+1}</div><div>
            <div class="news-title">${n.title} ${badge}</div>
            <div class="news-meta">${n.pubDate}</div>
            <div class="news-desc">${n.desc}</div>
            <a class="news-link" href="${n.link}" target="_blank">Read article -&gt;</a>
          </div></div>`;
        }).join('');
      }
      document.getElementById('newsHeader').textContent = `Top News ${newsItems.length}`;
      const sc = sent.score;
      const sColor = sc > 0 ? '#27ae60' : sc < 0 ? '#e74c3c' : '#f39c12';
      const sLabel = sc > 0 ? 'Positive' : sc < 0 ? 'Negative' : 'Neutral';
      const card = document.getElementById('sentimentCard');
      if (card) {
        card.style.borderLeftColor = sColor;
        document.getElementById('sentScore').style.color = sColor;
        document.getElementById('sentScore').innerHTML = `${sc >= 0 ? '+' : ''}${sc} <span class="sent-label" id="sentLabel">${sLabel}</span>`;
        const total = newsItems.length;
        document.getElementById('sentPos').parentElement.style.width = `${sent.pos/total*100}%`;
        document.getElementById('sentNeu').parentElement.style.width = `${sent.neu/total*100}%`;
        document.getElementById('sentNeg').parentElement.style.width = `${sent.neg/total*100}%`;
        document.getElementById('sentPos').textContent = sent.pos;
        document.getElementById('sentNeu').textContent = sent.neu;
        document.getElementById('sentNeg').textContent = sent.neg;
        document.getElementById('sentDesc').textContent = `Based on ${total} news (refreshed). Scores reflected in signals.`;
      }
    }
    const newDates = rows.map(r => r.date);
    const newCloses = rows.map(r => Math.round(r.close));
    const newVols = rows.map(r => Math.round(r.volume));
    const ma20Arr = sma(rows.map(r => r.close), 20).map(v => v == null ? null : Math.round(v));
    const ma60Arr = sma(rows.map(r => r.close), 60).map(v => v == null ? null : Math.round(v));
    const rsiArr = calcRSI(rows.map(r => r.close), 14);
    const bb = calcBB(rows.map(r => r.close), 20, 2);
    const bbUpperArr = bb.upper.map(v => v == null ? null : Math.round(v));
    const bbLowerArr = bb.lower.map(v => v == null ? null : Math.round(v));
    const mc = calcMACD(rows.map(r => r.close));
    const macdArr = mc.macd.map(v => v == null ? null : Math.round(v));
    const macdSigArr = mc.signal.map(v => v == null ? null : Math.round(v));
    const macdHistArr = mc.hist.map(v => v == null ? null : Math.round(v));

    const cur = rows[rows.length - 1].close;
    const hi = Math.max(...rows.map(r => r.close));
    const lo = Math.min(...rows.map(r => r.close));
    const pos = hi > lo ? (cur - lo) / (hi - lo) * 100 : 50;
    const curMa20 = ma20Arr[ma20Arr.length - 1];
    const curMa60 = ma60Arr[ma60Arr.length - 1];
    const curRsi = rsiArr[rsiArr.length - 1];
    const curBbU = bb.upper[bb.upper.length - 1];
    const curBbL = bb.lower[bb.lower.length - 1];
    const curBbW = bb.width[bb.width.length - 1];
    const bbPos = (curBbU != null && curBbL != null && curBbU > curBbL)
      ? (cur - curBbL) / (curBbU - curBbL) * 100 : 50;
    const curMacd = mc.macd[mc.macd.length - 1];
    const curMacdSig = mc.signal[mc.signal.length - 1];
    const curMacdHist = mc.hist[mc.hist.length - 1];
    const macdTrend = mc.hist.slice(-3).filter(v => v != null).length >= 2
      ? (mc.hist[mc.hist.length - 1] || 0) - (mc.hist[mc.hist.length - 3] || 0) : 0;
    const sig = calcSignal(cur, curMa20, curMa60, curRsi, pos, bbPos, curBbW, curMacd, curMacdSig, curMacdHist, macdTrend, sentScore);

    // update canvas chart data and redraw
    closes.length = 0; closes.push(...newCloses);
    ma20.length = 0; ma20.push(...ma20Arr);
    ma60.length = 0; ma60.push(...ma60Arr);
    bbUpper.length = 0; bbUpper.push(...bbUpperArr);
    bbLower.length = 0; bbLower.push(...bbLowerArr);
    volumes.length = 0; volumes.push(...newVols);
    macdLine.length = 0; macdLine.push(...macdArr);
    macdSignal.length = 0; macdSignal.push(...macdSigArr);
    macdHist.length = 0; macdHist.push(...macdHistArr);
    dates.length = 0; dates.push(...newDates);
    drawPriceChart(); drawVolChart(); drawMACDChart(); drawATRADXChart(); drawKDJChart(); drawVolMaChart();

    // update text
    const nf = n => Math.round(n).toLocaleString();
    document.getElementById('priceText').textContent = `${nf(cur)} KRW`;
    document.getElementById('hiText').textContent = `${nf(hi)} KRW`;
    document.getElementById('loText').textContent = `${nf(lo)} KRW`;
    document.getElementById('posText').textContent = `${Math.round(pos)}%`;
    document.getElementById('posBar').style.width = `${Math.round(pos)}%`;
    if (curMa20 != null) document.getElementById('ma20Text').textContent = `${nf(curMa20)} KRW`;
    if (curMa60 != null) document.getElementById('ma60Text').textContent = `${nf(curMa60)} KRW`;
    if (curRsi != null) document.getElementById('rsiText').textContent = curRsi.toFixed(1);
    if (curBbU != null) document.getElementById('bbUpperText').textContent = `${nf(curBbU)} KRW`;
    if (curBbL != null) document.getElementById('bbLowerText').textContent = `${nf(curBbL)} KRW`;
    if (curBbW != null) document.getElementById('bbWidthText').textContent = `${curBbW.toFixed(1)}% / ${Math.round(bbPos)}%`;
    if (curMacd != null) document.getElementById('macdText').textContent = `${Math.round(curMacd)} / ${Math.round(curMacdSig)}`;
    if (curMacdHist != null) document.getElementById('macdHistText').textContent = `${curMacdHist >= 0 ? '+' : ''}${Math.round(curMacdHist)}`;

    // recommendation box
    const colors = { BUY: "#27ae60", SELL: "#e74c3c", HOLD: "#f39c12" };
    const box = document.getElementById('actionBox');
    box.style.background = colors[sig.action];
    document.getElementById('actionLabel').textContent = sig.label;
    document.getElementById('actionScore').textContent = `Score: ${sig.score >= 0 ? '+' : ''}${sig.score} (BUY>=2 / SELL<=-2 / HOLD)`;

    // reasoning
    document.getElementById('reasonsList').innerHTML = sig.reasons.map(r => `<li>${r}</li>`).join('');

    // date
    const today = new Date().toISOString().slice(0, 10);
    document.getElementById('subText').textContent = `Date ${today} ?? Recent ${MONTHS}mo data ?? Tech analysis (refreshed)`;

    showToast(`Updated ?? ${nf(cur)} KRW`);
  } catch (e) {
    showToast(`Update fail: ${e.message}`, true);
  } finally {
    btn.disabled = false;
    btn.classList.remove('loading');
  }
}

// ===== Draw all canvas charts on load =====
function drawAll(){
  drawPriceChart(); drawVolChart(); drawMACDChart(); drawATRADXChart(); drawKDJChart(); drawVolMaChart();
}
window.addEventListener('load', function(){
  drawAll();
  setTimeout(refreshData, 1500);
});
window.addEventListener('resize', function(){ drawAll(); });
