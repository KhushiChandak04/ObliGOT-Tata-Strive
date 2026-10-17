import PageHeader from "../components/ui/PageHeader";
import StateMessage from "../components/ui/StateMessage";
export default function ProjectsPage() {
  return <>
    <PageHeader eyebrow="PARTNERSHIP OPERATIONS" title="Projects & milestones" description="Review project status, delivery milestones, and upcoming obligations." />
    <div className="panel placeholder-panel">
      <div className="placeholder-symbol">P</div>
      <h2>Feature scaffold ready</h2>
      <p>This route and page shell are wired. Connect the relevant API and persistent data before using this workflow operationally.</p>
      <StateMessage title="No live records connected yet" detail="This starter intentionally avoids presenting fabricated metrics or fake actions as real data." />
    </div>
  </>;
}
