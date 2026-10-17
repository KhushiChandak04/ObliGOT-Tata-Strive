import type { ReactNode } from "react";
export default function PageHeader({eyebrow,title,description,action}:{eyebrow?:string;title:string;description:string;action?:ReactNode}) {
  return <div className="page-header"><div>{eyebrow&&<div className="eyebrow">{eyebrow}</div>}<h1>{title}</h1><p>{description}</p></div>{action&&<div>{action}</div>}</div>;
}
