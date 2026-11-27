"""Ninth Circuit ordinary merits-panel guards; exceptions intentionally unsupported."""
def check_panel(state, case, require):
    panel = case["assigned_judges"]
    require(isinstance(panel, list) and len(panel) == len(set(panel)) == 3,
            "CA9 ordinary merits panel requires three distinct judges")
    people = [state["people"].get(i, {}) for i in panel]
    require(all(p.get("role") == "judge" and p.get("active") is True for p in people), "CA9 panel member unavailable")
    require(all(p.get("judicial_status") in {"active_circuit", "senior_circuit", "visiting"} for p in people), "CA9 judge status missing")
    members = [p for p in people if p.get("court_id") == "CA9" and p.get("judicial_status") in {"active_circuit","senior_circuit"}]
    active = [p for p in members if p["judicial_status"] == "active_circuit"]
    require(len(members) >= 2 and active, "CA9 panel must include two Ninth members, one active")
    require(all(type(p.get("seniority_rank")) is int and p["seniority_rank"] > 0 for p in active), "CA9 active judge seniority missing")
    require(len({p["seniority_rank"] for p in active}) == len(active), "CA9 seniority ranks tied")
    chiefs = [p for p in active if p.get("chief_judge") is True]
    require(len(chiefs) <= 1, "multiple chief judges")
    expected = (chiefs[0] if chiefs else min(active,key=lambda p:p["seniority_rank"]))["id"]
    require(case.get("presiding_judge_id") == expected, "CA9 presiding judge incorrect")
    require(case.get("conflict_review_completed") is True and case.get("jurisdiction_basis"), "CA9 case needs jurisdiction and conflict review")
    require(case.get("panel_kind") == "ordinary_merits", "CA9 special panels not implemented")

def no_argument(case, p, require):
    require(p.get("briefs_and_record_reviewed") is True, "FRAP 34 record review required")
    votes = p.get("no_argument_votes", {})
    require(set(votes) == set(case["assigned_judges"]) and all(v is True for v in votes.values()), "FRAP 34 requires unanimous no-argument decision")
    require(p.get("no_argument_reason") in {"frivolous","authoritatively_decided","argument_not_helpful"}, "FRAP 34 reason required")

def conference(case,p,require):
    require(any(h["status"]=="completed" and h.get("panel_epoch")==case.get("panel_epoch") for h in case["hearings"].values()), "CA9 submit appeal before conference")
    votes=p.get("votes",{})
    require(set(votes)==set(case["assigned_judges"]), "CA9 conference votes incomplete")
    require(all(isinstance(v,str) and v.strip() for v in votes.values()), "CA9 disposition vote missing")
    disposition=p.get("majority_disposition")
    coalition=[j for j,v in votes.items() if v==disposition]
    require(len(coalition)>=len(case["assigned_judges"])//2+1 and p.get("author_id") in coalition, "CA9 majority and author required")
    return {"votes":dict(votes),"majority_disposition":disposition,"author_id":p["author_id"]}

def issuance(case, opinion, p, require):
    kind=p["opinion_kind"]
    form=p.get("publication_form")
    require(form in {"OPINION","MEMORANDUM","ORDER"}, "CA9 disposition form required")
    require(p.get("certified") is True, "CA9 written disposition certification required")
    require(all(v["stance"]!="pending" for v in opinion["positions"].values()), "CA9 final positions required")
    if kind in {"majority","plurality","order"}:
        disposition=p.get("disposition")
        require(isinstance(disposition,str) and disposition.strip(), "CA9 disposition required")
        require(sum(v["disposition"]==disposition for v in opinion["positions"].values())>=len(case["assigned_judges"])//2+1,"CA9 disposition lacks majority")
        require(opinion["positions"][opinion["author_id"]]["disposition"]==disposition,"CA9 author disagrees with disposition")
        if kind=="majority":
            require(sum(v["disposition"]==disposition and v["stance"]=="join" and set(v["joined_parts"])==set(opinion["parts"]) for v in opinion["positions"].values())>=len(case["assigned_judges"])//2+1,"CA9 full majority reasoning not established")
    if form=="OPINION":
        require(p.get("publication_reason") in {"federal_rule","overlooked_rule","criticism","unique_or_public_importance","published_below","separate_expression_request"},"Circuit 36-2 publication reason required")
    return {"publication_form":form,"publication_reason":p.get("publication_reason"),"certified":True,"disposition":p.get("disposition")}
