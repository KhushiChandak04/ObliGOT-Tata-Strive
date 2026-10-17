import AuthStatus from "../components/ui/AuthStatus";
import { NavLink } from "react-router-dom";
import { Activity, Building2, CircleDollarSign, FileCheck2, FileText, Gauge, Handshake, Layers3, ListTodo, Upload } from "lucide-react";
import AppRouter from "./router";
const nav = [
  {to:"/",label:"Overview",icon:Gauge,end:true},{to:"/partners",label:"Partners",icon:Building2},
  {to:"/pipeline",label:"Pipeline",icon:Layers3},{to:"/agreements",label:"Agreements",icon:FileCheck2},
  {to:"/projects",label:"Projects",icon:Handshake},{to:"/finance",label:"Finance",icon:CircleDollarSign},
  {to:"/reports",label:"Reports",icon:FileText},{to:"/actions",label:"Action center",icon:ListTodo},
  {to:"/import",label:"Import data",icon:Upload}
];
export default function App() {
  return <div className="app-shell">
    <aside className="sidebar"><div className="brand"><div className="brand-mark">O</div><div><strong>ObliGOT</strong><span>Partnership command center</span></div></div>
      <div className="workspace-label">WORKSPACE</div><nav className="navigation">
        {nav.map(({to,label,icon:Icon,end})=><NavLink key={to} to={to} end={end} className={({isActive})=>`nav-link ${isActive?"active":""}`}><Icon size={17}/><span>{label}</span></NavLink>)}
      </nav><div className="sidebar-bottom"><div className="status-dot"/><div><strong>Demo workspace</strong><span>Illustrative data · not verified</span></div></div>
    </aside>
    <main className="main-area"><header className="topbar"><div className="breadcrumb">Workspace <span>/</span> <strong>Partnerships</strong></div><div className="topbar-right"><span className="environment-pill">DEMO ENVIRONMENT</span><AuthStatus /><div className="avatar">OG</div></div></header>
      <div className="page-container"><AppRouter/></div><footer className="app-footer"><span>ObliGOT · Partnership Command Center</span><span><Activity size={13}/> Operational visibility, with human review</span></footer>
    </main>
  </div>;
}
