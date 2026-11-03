import { useEffect, useRef } from 'react'
import { CandlestickSeries, ColorType, createChart, createSeriesMarkers, type SeriesMarker, type Time } from 'lightweight-charts'
type Bar={time:string;open:number;high:number;low:number;close:number}
// STK-079: ex-date markers are labels only; they never adjust plotted prices.
export type ChartEvent={date:string;kind:'dividend'|'share';text:string}

export const placeEvents=(bars:Bar[],events:ChartEvent[])=>{
 if(!bars.length)return []
 const first=bars[0].time,last=bars[bars.length-1].time
 return events.filter(e=>e.date>=first&&e.date<=last).map(e=>({...e,time:bars.find(b=>b.time>=e.date)!.time}))
}

export function Chart({bars,real=false,cutoff,events=[]}:{bars:Bar[];real?:boolean;cutoff?:string;events?:ChartEvent[]}){
 const ref=useRef<HTMLDivElement>(null)
 const placed=placeEvents(bars,events)
 useEffect(()=>{if(!ref.current)return;const c=createChart(ref.current,{height:340,autoSize:true,layout:{background:{type:ColorType.Solid,color:'#101922'},textColor:'#aec1cf',attributionLogo:true},grid:{vertLines:{color:'#1e2c36'},horzLines:{color:'#1e2c36'}}});const series=c.addSeries(CandlestickSeries,{upColor:'#91dfbf',downColor:'#ec9a92',borderVisible:false});series.setData(bars)
  const markers:SeriesMarker<Time>[]=placed.map(e=>({time:e.time,position:'belowBar',color:e.kind==='dividend'?'#7cc4f2':'#d8a7f0',shape:'circle',text:e.kind==='dividend'?'D':'B/S'}))
  if(cutoff&&bars.some(b=>b.time===cutoff.slice(0,10)))markers.push({time:cutoff.slice(0,10),position:'aboveBar',color:'#f6cf72',shape:'arrowDown',text:'Historical cutoff'})
  if(markers.length)createSeriesMarkers(series,markers.sort((a,b)=>String(a.time).localeCompare(String(b.time))))
  c.timeScale().fitContent();return()=>c.remove()},[bars,cutoff,JSON.stringify(placed)])
 return <><div className="candle-chart" ref={ref} aria-label={`Daily candlestick chart, ${bars.length} ${real?'observed':'fictional'} candles${placed.length?`, ${placed.length} ex-date markers`:''}`}/>
  {placed.length>0&&<ul className="chart-events" data-testid="chart-ex-dates">{placed.map(e=><li key={e.date+e.text}>{e.kind==='dividend'?'D':'B/S'} {e.date}{e.time!==e.date?` (shown on ${e.time})`:''} · {e.text}</li>)}</ul>}
  <p className="attribution">Charts by <a href="https://www.tradingview.com/" target="_blank" rel="noreferrer">TradingView</a> · Lightweight Charts™. Copyright © 2025 TradingView, Inc. · <a href="/THIRD-PARTY-NOTICES.txt" target="_blank" rel="noreferrer">Third-party licences</a></p></>
}
