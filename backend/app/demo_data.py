from datetime import timedelta
from app.models import Partner, ActionItem
from app.rules import business_today

today = business_today()
# Clearly labelled illustrative records; no real partner commitments are implied.
PARTNERS = {
    "demo-001": Partner(id="demo-001", name="Illustrative Skills Partner", category="Training & curriculum", contribution_types=["curriculum", "training"], status="active", owner="Partnerships Team", updated_at=today, summary="Illustrative record only. Not a verified organization or commitment.", source_label="demo"),
    "demo-002": Partner(id="demo-002", name="Illustrative Industry Partner", category="Industry collaboration", contribution_types=["industry expertise"], status="qualification", owner="Regional Partnerships", updated_at=today, summary="Illustrative prospect record. Validate all details before operational use.", source_label="demo"),
    "demo-003": Partner(id="demo-003", name="Illustrative Community Partner", category="Implementation", contribution_types=["implementation"], status="prospect", owner="Program Team", updated_at=today, summary="Illustrative pipeline record.", source_label="demo"),
}
ACTIONS = {
    "demo-action-001": ActionItem(id="demo-action-001", title="Confirm next reporting date for sample project", priority="high", status="open", due_date=today + timedelta(days=2), evidence=["Demo record has no verified reporting date attached."], recommended_action="Confirm the reporting schedule with the record owner and update the source record.", owner="Partnerships Team", source_label="demo"),
    "demo-action-002": ActionItem(id="demo-action-002", title="Review agreement dates before enabling expiry alerts", priority="medium", status="open", due_date=today + timedelta(days=7), evidence=["No verified agreement date is present in the starter dataset."], recommended_action="Enter and verify the signed agreement's effective and expiry dates.", owner="Partnerships Team", source_label="demo"),
}
FOLLOWUPS = {}
