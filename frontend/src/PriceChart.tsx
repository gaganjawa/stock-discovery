import { useEffect, useRef } from 'react'
import { CandlestickSeries, ColorType, createChart, createSeriesMarkers } from 'lightweight-charts'
type Bar={time:string;open:number;high:number;low:number;close:number}
export function Chart({bars,real=false,cutoff}:{bars:Bar[];real?:boolean;cutoff?:string}){
 const ref=useRef<HTMLDivElement>(null)
 useEffect(()=>{if(!ref.current)return;const c=createChart(ref.current,{height:340,autoSize:true,layout:{background:{type:ColorType.Solid,color:'#101922'},textColor:'#aec1cf',attributionLogo:true},grid:{vertLines:{color:'#1e2c36'},horzLines:{color:'#1e2c36'}}});const series=c.addSeries(CandlestickSeries,{upColor:'#91dfbf',downColor:'#ec9a92',borderVisible:false});series.setData(bars);if(cutoff&&bars.some(b=>b.time===cutoff.slice(0,10)))createSeriesMarkers(series,[{time:cutoff.slice(0,10),position:'aboveBar',color:'#f6cf72',shape:'arrowDown',text:'Historical cutoff'}]);c.timeScale().fitContent();return()=>c.remove()},[bars,cutoff])
 return <><div className="candle-chart" ref={ref} aria-label={`Daily candlestick chart, ${bars.length} ${real?'observed':'fictional'} candles`}/><p className="attribution">Charts by <a href="https://www.tradingview.com/" target="_blank" rel="noreferrer">TradingView</a> · Lightweight Charts™. Copyright © 2025 TradingView, Inc. · <a href="/THIRD-PARTY-NOTICES.txt" target="_blank" rel="noreferrer">Third-party licences</a></p></>
}
