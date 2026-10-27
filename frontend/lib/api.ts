export const API=process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
export async function api(path:string, options:RequestInit={}) {
 const form=options.body instanceof FormData;
 const r=await fetch(API+'/api'+path,{...options,credentials:'include',headers:{...(!form?{'Content-Type':'application/json'}:{}),'X-CareerOrbit-Request':'1',...options.headers}});
 if(!r.ok) {const d=await r.json().catch(()=>({detail:r.statusText}));throw new Error(typeof d.detail==='string'?d.detail:JSON.stringify(d.detail));}
 return r.status===204?null:r.json();
}
export function post(path:string, body:unknown={}) {return api(path,{method:'POST',body:JSON.stringify(body)});}
export function safeUrl(url:string) {try {const u=new URL(url);return ['https:','http:'].includes(u.protocol)?url:'#';}catch{return '#';}}
