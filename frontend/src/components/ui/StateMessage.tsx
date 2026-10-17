export default function StateMessage({title,detail,kind="empty"}:{title:string;detail?:string;kind?:"error"|"empty"|"loading"}) {
  return <div className={`state-message ${kind}`}><strong>{title}</strong>{detail&&<p>{detail}</p>}</div>;
}
