import { ReactNode } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { ShieldCheck, LayoutDashboard, ScanLine, History, LogOut } from 'lucide-react';
import { clearAuth } from '../lib/api';

export default function Layout({children}:{children:ReactNode}){
 const nav=useNavigate();
 const links=[['/','Dashboard',LayoutDashboard],['/scan','New Scan',ScanLine],['/history','History',History]] as const;
 return <div className="min-h-screen bg-slate-950 text-slate-100 flex">
  <aside className="hidden md:flex w-64 border-r border-slate-800 bg-slate-950/90 p-5 flex-col fixed inset-y-0">
   <div className="flex items-center gap-3 mb-10"><div className="p-2 rounded-xl bg-cyan-400/10 text-cyan-300"><ShieldCheck/></div><div><div className="font-bold">PrivacyGuard</div><div className="text-xs text-slate-500">Risk Detection System</div></div></div>
   <nav className="space-y-2">{links.map(([to,label,Icon])=><NavLink key={to} to={to} className={({isActive})=>`flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm ${isActive?'bg-cyan-400/10 text-cyan-300':'text-slate-400 hover:bg-slate-900 hover:text-white'}`}><Icon size={18}/>{label}</NavLink>)}</nav>
   <div className="mt-auto"><button onClick={()=>{clearAuth();nav('/login')}} className="flex items-center gap-3 text-slate-400 hover:text-white px-3 py-2.5"><LogOut size={18}/>Logout</button></div>
  </aside>
  <main className="md:ml-64 flex-1 min-w-0"><header className="md:hidden sticky top-0 z-20 bg-slate-950/90 backdrop-blur border-b border-slate-800 px-4 py-3 flex justify-between"><b>PrivacyGuard</b><button onClick={()=>{clearAuth();nav('/login')}}><LogOut size={18}/></button></header>{children}</main>
 </div>
}
