import type { ReactNode } from "react";
export default function StateMessage({title,detail,kind="empty",action}:{title:string;detail?:string;kind?:"error"|"empty"|"loading";action?:ReactNode}) {
  return <div className={`state-message ${kind}`} role={kind==="error"?"alert":kind==="loading"?"status":undefined}><strong>{title}</strong>{detail&&<p>{detail}</p>}{action&&<div className="state-action">{action}</div>}</div>;
}
