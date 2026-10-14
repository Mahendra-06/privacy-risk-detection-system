const API = import.meta.env.VITE_API_URL ?? 'http://localhost:4001/api';
export function token(){ return localStorage.getItem('privacy_token'); }
export function setAuth(t:string){ localStorage.setItem('privacy_token',t); }
export function clearAuth(){ localStorage.removeItem('privacy_token'); }
async function request(path:string, options:RequestInit={}){
  const headers = new Headers(options.headers); if (!(options.body instanceof FormData)) headers.set('Content-Type','application/json');
  const t=token(); if(t) headers.set('Authorization',`Bearer ${t}`);
  const res=await fetch(`${API}${path}`,{...options,headers}); const data=await res.json().catch(()=>({}));
  if(!res.ok) {
    if (res.status === 401 && !path.startsWith('/auth/login') && !path.startsWith('/auth/register')) {
      clearAuth();
      if (typeof window !== 'undefined' && window.location.pathname !== '/login' && window.location.pathname !== '/register') {
        window.location.href = '/login';
      }
    }
    throw new Error(data.message ?? 'Request failed');
  }
  return data;
}
export const api={
  register:(body:any)=>request('/auth/register',{method:'POST',body:JSON.stringify(body)}),
  login:(body:any)=>request('/auth/login',{method:'POST',body:JSON.stringify(body)}),
  me:()=>request('/auth/me'),
  summary:()=>request('/dashboard/summary'),
  scans:()=>request('/scans'),
  scan:(id:string)=>request(`/scans/${id}`),
  text:(text:string, redactionMode:string='tagged')=>request('/scans/text',{method:'POST',body:JSON.stringify({text, redactionMode})}),
  document:(file:File, redactionMode:string='tagged')=>{const f=new FormData();f.append('file',file);f.append('redactionMode',redactionMode);return request('/scans/document',{method:'POST',body:f})}
};
