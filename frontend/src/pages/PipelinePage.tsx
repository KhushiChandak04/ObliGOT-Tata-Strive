import PageHeader from "../components/ui/PageHeader";
import StateMessage from "../components/ui/StateMessage";
export default function PipelinePage() {
  return <>
    <PageHeader eyebrow="PARTNERSHIP OPERATIONS" title="Partnership pipeline" description="Track prospective partnerships through qualification, proposal, approval, and agreement." />
    <div className="panel placeholder-panel">
      <div className="placeholder-symbol">P</div>
      <h2>Feature scaffold ready</h2>
      <p>This route and page shell are wired. Connect the relevant API and persistent data before using this workflow operationally.</p>
      <StateMessage title="No live records connected yet" detail="This starter intentionally avoids presenting fabricated metrics or fake actions as real data." />
    </div>
  </>;
}
