"""CA9 procedural simulation v2. Reviewed inputs are not automated legal findings."""
from copy import deepcopy
from datetime import timedelta, date
from hashlib import sha256
from zoneinfo import ZoneInfo

EVENTS = {
    "ca9.assign", "ca9.panel_change", "ca9.judgment", "ca9.rehearing_file",
    "ca9.response_request", "ca9.response_file", "ca9.panel_rehearing",
    "ca9.en_banc_call", "ca9.en_banc_open", "ca9.en_banc_vote", "ca9.en_banc_tally",
    "ca9.en_banc_draw", "ca9.en_banc_clear", "ca9.stay_file", "ca9.stay_decide",
    "ca9.stay_end", "ca9.mandate", "ca9.mandate_recall"
}

def init_case(c, require):
    require(c["assigned_judges"] == [], "CA9 register unassigned; use ca9.assign")
    require(c.get("jurisdiction_basis") and c.get("conflict_review_completed") is True,
            "CA9 reviewed jurisdiction and conflict screening required")
    require(c.get("panel_kind") == "ordinary_merits", "unsupported initial panel")
    require(c.get("origin_district") and c.get("calendar_location"), "origin and calendar location required")
    c.update(phase="unassigned", panel_epoch=0, panel_history=[], excluded_judges=[],
             judgment_history=[], review_history=[], review=None, judgment=None, mandate=None)

def member(p):
    return p.get("role")=="judge" and p.get("active") is True and p.get("court_id")=="CA9"

def active(p):
    return member(p) and p.get("judicial_status")=="active_circuit"

def majority(c):
    return len(c["assigned_judges"])//2+1

def draw(seed, pool, salt):
    # Stable simulated lottery; seed logged, not cryptographic proof of fair random input.
    return sorted(pool, key=lambda j:(sha256((seed+"|"+salt+"|"+j).encode()).hexdigest(),j))

def eligible(s,c, voting=False):
    return sorted(j for j,p in s["people"].items() if active(p) and j not in c["excluded_judges"]
                  and (not voting or not p.get("en_banc_transition_recusal",False)))

def presider(s,panel,require):
    act=[s["people"][j] for j in panel if active(s["people"][j])]
    require(act and all(type(p.get("seniority_rank")) is int and p["seniority_rank"]>0 for p in act), "active seniority missing")
    require(len({p["seniority_rank"] for p in act})==len(act),"seniority tied")
    chiefs=[p for p in act if p.get("chief_judge") is True]
    require(len(chiefs)<=1,"multiple chiefs")
    return (chiefs[0] if chiefs else min(act,key=lambda p:p["seniority_rank"]))["id"]

def set_panel(s,c,panel,kind,reason,now,require):
    c["panel_epoch"]+=1
    c["assigned_judges"]=list(panel)
    c["panel_kind"]=kind
    # A lawful two-judge quorum may contain no active Ninth judge after loss.
    c["presiding_judge_id"]=presider(s,panel,require) if any(active(s["people"][j]) for j in panel) else panel[0]
    c["panel_history"].append({"epoch":c["panel_epoch"],"judges":list(panel),"kind":kind,"reason":reason,"at":now})

def date_due(start,days,holidays):
    d=start+timedelta(days=days)
    while d.weekday()>=5 or d.isoformat() in holidays:
        d+=timedelta(days=1)
    return d

def local_date(value,moment):
    return moment(value).astimezone(ZoneInfo("America/Los_Angeles")).date()

def reviewed(p,require):
    require(p.get("legal_review_completed") is True and isinstance(p.get("rule_basis"),str) and p["rule_basis"].strip(),
            "reviewed rule/order basis required")

def doc(s,c,p,key,require,judge_document):
    d=judge_document(s,p[key])
    require(d["case_id"]==c["id"] and d["status"]=="filed","filed same-case document required")
    return d["id"]

def phase(c,*allowed,require):
    require(c.get("phase") in allowed,"CA9 wrong procedural phase: "+str(c.get("phase")))

def archived_round(s,c,now,why,withdraw=False):
    # Old opinions remain readable with their historical panel and epoch.
    for o in s["opinions"].values():
        if o["case_id"]!=c["id"] or o.get("panel_epoch")!=c["panel_epoch"]: continue
        if o["status"]=="circulating": o.update(status="superseded",superseded_at=now)
        elif withdraw and o["status"]=="issued":
            o.update(status="vacated",vacated_at=now,vacatur_reason=why)
            for pr in s["precedents"].values():
                if pr["opinion_id"]==o["id"]:
                    pr.update(previous_authority_status=pr["authority_status"],authority_status="nonprecedential",vacated_at=now)
    if withdraw and c["judgment"]:
        old=deepcopy(c["judgment"]);old.update(status="vacated",reason=why,at=now)
        c["judgment_history"].append(old);c["judgment"]=None
    if withdraw and c["review"]:
        c["review_history"].append(deepcopy(c["review"]));c["review"]=None
    c["writing_status"]="not_started"
    for h in c["hearings"].values():
        if h["status"]=="in_progress": h["status"]="cancelled"

def validate(s,c,require):
    ph=c.get("phase")
    require(ph in {"unassigned","merits","judgment","en_banc_pending","mandate_issued"},"invalid CA9 phase")
    if ph=="unassigned":
        require(not c["assigned_judges"] and c["panel_epoch"]==0,"unassigned case has panel")
        return
    panel=c["assigned_judges"];kind=c["panel_kind"]
    require(len(set(panel))==len(panel) and not set(panel)&set(c["excluded_judges"]),"invalid panel membership")
    require(c["panel_history"][-1]["judges"]==panel,"panel history mismatch")
    if kind=="quorum":
        require(len(panel)==2 and any(x["kind"]=="ordinary_merits" for x in c["panel_history"]),"invalid quorum")
    elif kind=="limited_en_banc":
        require(len(panel)==11 and all(member(s["people"][j]) for j in panel),"invalid en banc court")
        require(c["presiding_judge_id"]==presider(s,panel,require),"invalid en banc presider")
    else:
        from .ca9 import check_panel
        check_panel(s,c,require)
    if ph in {"judgment","mandate_issued","en_banc_pending"}:
        require(c["judgment"] is not None and c["review"] is not None,"missing judgment/review")
    if ph=="mandate_issued":
        require(c["mandate"] and c["status"]=="closed","mandate not closed")

def handle(s, kind, p, now, require, moment, judge_document):
    c=s["cases"][p["case_id"]]
    require(c["court_id"]=="CA9","CA9 event requires CA9 case")
    reviewed(p,require)
    today=local_date(now,moment)
    r=c.get("review")
    if kind=="ca9.assign":
        phase(c,"unassigned",require=require)
        # Clerk provides preconstituted sitting slots, not a hand-picked judge for a case.
        seed=p["seed"];require(isinstance(seed,str) and len(seed)>=8,"record draw seed")
        require(type(p["case_weight"]) is int and p["case_weight"]>0,"invalid case weight")
        require(p.get("calendar_review_completed") is True,"calendar availability and conflict review required")
        slots=p["slots"];require(isinstance(slots,list) and slots,"calendar slots required")
        from .ca9 import check_panel
        options={}
        for slot in slots:
            sid=slot["id"]; require(sid not in options,"duplicate slot")
            if slot["location"]!=c["calendar_location"] or slot["month"]!=p["calendar_month"]: continue
            panel=slot["judges"]
            if set(panel)&set(c["excluded_judges"]+slot.get("conflicts",[])): continue
            if any(s["people"][j].get("district_judge_district")==c["origin_district"] for j in panel): continue
            if type(slot["remaining_weight"]) is not int or slot["remaining_weight"]<p["case_weight"]: continue
            candidate=dict(c,assigned_judges=panel,presiding_judge_id=presider(s,panel,require))
            check_panel(s,candidate,require)
            options[sid]=slot
        require(type(p["case_weight"]) is int and p["case_weight"]>0 and options,"no eligible sitting slot")
        sid=draw(seed,options,c["id"])[0]
        c["assignment"]={"slot_id":sid,"seed":seed,"eligible_slots":sorted(options),"calendar_month":p["calendar_month"],"weight":p["case_weight"],"priority_review":p.get("priority_review"),"at":now}
        require(p.get("priority_review"),"GO 3.3(c) priority review required")
        set_panel(s,c,options[sid]["judges"],"ordinary_merits","clerk_calendar_draw",now,require);c["phase"]="merits"
    elif kind=="ca9.panel_change":
        phase(c,"merits",require=require)
        require(c["panel_kind"]!="quorum","second loss from quorum requires special review")
        require(not any(o["case_id"]==c["id"] and o.get("panel_epoch")==c["panel_epoch"] and o["status"]=="issued" for o in s["opinions"].values()),"panel loss after opinion issuance requires separate review")
        old=c["assigned_judges"];out=p["outgoing_judge_id"]
        require(out in old and p["reason"] in {"recusal","disqualification","death","disability","retirement","unavailability"},"invalid panel loss")
        remaining=[j for j in old if j!=out]
        submitted=any(h["status"]=="completed" and h.get("panel_epoch")==c["panel_epoch"] for h in c["hearings"].values())
        c["excluded_judges"].append(out)
        if p.get("mode")=="quorum":
            require(c["panel_kind"]=="ordinary_merits" and submitted and p["reason"]!="unavailability","quorum only after qualifying loss after submission")
            votes=p["remaining_votes"]
            require(set(votes)==set(remaining) and len(set(votes.values()))==1 and all(votes.values()),"remaining judges must agree")
            archived_round(s,c,now,"panel_loss")
            set_panel(s,c,remaining,"quorum","GO 3.2.h",now,require)
            c["quorum_disposition"]=next(iter(votes.values()))
            c["hearings"]["QUORUM-"+str(c["panel_epoch"])]={"id":"QUORUM-"+str(c["panel_epoch"]),"kind":"consideration_on_briefs","status":"completed","panel_epoch":c["panel_epoch"],"started_at":now,"ended_at":now,"basis":"continued submission under 28 USC 46(d)"}
        else:
            mode=p.get("mode")
            require(mode in {"same_location_switch","lot"},"replacement mode required")
            require(p.get("parties_notified") is True,"clerk notice required")
            if mode=="lot":require(isinstance(p["seed"],str) and len(p["seed"])>=8,"record draw seed")
            if c["panel_kind"]=="limited_en_banc":
                require(mode=="lot","en banc replacement by alternate or lot")
                pool=[j for j in eligible(s,c) if j not in remaining]
                alts=[j for j in c.get("en_banc_alternates",[]) if j in pool]
                incoming=alts[0] if alts else draw(p["seed"],pool,c["id"]+"replacement")[0] if pool else None
                require(incoming,"no eligible replacement")
                c["en_banc_alternates"]=[j for j in alts if j!=incoming]
            elif mode=="same_location_switch":
                require(not submitted and p.get("same_location_review") is True,"switch only before submission")
                incoming=p["incoming_judge_id"]
                require(incoming not in remaining+c["excluded_judges"],"excluded replacement")
            else:
                if not submitted: require(p.get("switch_unavailable") is True,"try same-location switch first")
                pool=[j for j in eligible(s,c) if j not in remaining]
                if submitted:
                    pool+= [j for j,x in s["people"].items() if member(x) and x.get("judicial_status")=="senior_circuit" and x.get("willing_replacement") is True and j not in remaining+c["excluded_judges"]]
                require(pool,"no eligible replacement")
                incoming=draw(p["seed"],pool,c["id"]+"replacement")[0]
            archived_round(s,c,now,"panel_loss")
            set_panel(s,c,remaining+[incoming],c["panel_kind"],p["reason"],now,require)
            # Conservative simulation: resubmit on current panel before new conference.
    elif kind=="ca9.judgment":
        phase(c,"merits",require=require)
        o=s["opinions"][p["controlling_opinion_id"]]
        require(o["case_id"]==c["id"] and o.get("panel_epoch")==c["panel_epoch"] and o["status"]=="issued" and o["opinion_kind"] in {"majority","plurality","order"},"current controlling issued disposition required")
        require(not any(x["case_id"]==c["id"] and x.get("panel_epoch")==c["panel_epoch"] and x["status"]=="circulating" for x in s["opinions"].values()),"outstanding current drafts")
        if c["panel_kind"]=="quorum":require(o["disposition"]==c["quorum_disposition"],"quorum disagreement")
        jd=doc(s,c,p,"judgment_document_id",require,judge_document)
        require(p.get("calendar_verified") is True and type(p.get("federal_party_civil")) is bool,"FRAP 26 calendar and 40(d) party review required")
        require(not(p["federal_party_civil"] and c["matter_type"]=="criminal_appeal"),"45 days only civil")
        holidays=p["holidays"];require(isinstance(holidays,list) and all(date.fromisoformat(x).isoformat()==x for x in holidays),"invalid holidays")
        due=date_due(today,45 if p["federal_party_civil"] else 14,holidays)
        if p.get("rehearing_due_override"):
            doc(s,c,p,"deadline_order_id",require,judge_document)
            due=date.fromisoformat(p["rehearing_due_override"]);require(due>=today,"invalid adjusted due date")
        c["judgment"]={"document_id":jd,"opinion_id":o["id"],"disposition":o["disposition"],"entered_at":now,"epoch":c["panel_epoch"]}
        c["review"]={"petition_due":due.isoformat(),"holidays":holidays,"petitions":{},"en_banc":{"status":"open","call_due":date_due(due,7,holidays).isoformat()},"stay":None,"denials":[],"rule_basis":p["rule_basis"]}
        c["phase"]="judgment";c["writing_status"]="issued"
    elif kind=="ca9.rehearing_file":
        phase(c,"judgment",require=require)
        require(today<=date.fromisoformat(r["petition_due"]),"late petition; special relief not implemented")
        require(r["en_banc"]["status"] in {"open","called","voting"},"review already cleared")
        require(c["panel_kind"]!="limited_en_banc" or p["kind"]=="panel","full court rehearing not implemented")
        key=doc(s,c,p,"petition_document_id",require,judge_document)
        require(key not in r["petitions"] and p["kind"] in {"panel","en_banc","both"},"invalid petition")
        r["petitions"][key]={"kind":p["kind"],"panel":"pending" if p["kind"] in {"panel","both"} else "not_requested","en_banc":"pending" if p["kind"] in {"en_banc","both"} else "not_requested","filed_at":now,"response":"not_requested"}
    elif kind in {"ca9.response_request","ca9.response_file"}:
        phase(c,"judgment",require=require)
        q=r["petitions"][p["petition_document_id"]]
        require("pending" in (q["panel"],q["en_banc"]),"petition resolved")
        if kind=="ca9.response_request":
            require(q["response"]=="not_requested","response already requested")
            q.update(response="requested",response_order=doc(s,c,p,"order_document_id",require,judge_document))
        else:
            require(q["response"]=="requested","unsolicited response prohibited")
            q.update(response="filed",response_document=doc(s,c,p,"response_document_id",require,judge_document))
    elif kind=="ca9.panel_rehearing":
        phase(c,"judgment",require=require)
        require(r["en_banc"]["status"] in {"open","called","voting"},"en banc disposition already resolved")
        q=r["petitions"][p["petition_document_id"]];require(q["panel"]=="pending","no panel petition pending")
        votes=p["votes"];require(set(votes)==set(c["assigned_judges"]) and all(type(v) is bool for v in votes.values()),"complete panel vote required")
        grant=sum(votes.values())>=majority(c)
        if grant: require(q["response"]=="filed" or p.get("exception_reviewed") is True,"response ordinarily required before grant")
        doc(s,c,p,"order_document_id",require,judge_document)
        q.update(panel="granted" if grant else "denied",panel_votes=votes)
        if grant:
            require(r["en_banc"]["status"]=="open","grant during en banc call requires coordinator handling")
            require(not any(x["en_banc"]=="pending" for x in r["petitions"].values()),"combined grant/amendment with pending en banc petition requires special review")
            require(p.get("withdraw_prior_judgment") is True,"withdrawal path only; amended disposition exception not automated")
            archived_round(s,c,now,"panel_rehearing",True)
            set_panel(s,c,c["assigned_judges"],c["panel_kind"],"panel_rehearing",now,require);c["phase"]="merits"
        else:r["denials"].append(today.isoformat())
    elif kind=="ca9.en_banc_call":
        phase(c,"judgment",require=require)
        e=r["en_banc"];require(e["status"]=="open","call already active")
        require(c["panel_kind"]!="limited_en_banc","full court rehearing not implemented")
        caller=p["judge_id"];require(member(s["people"][caller]) and caller not in c["excluded_judges"],"ineligible calling judge")
        # Petition/notice deadlines can vary; use reviewed absolute deadline with source.
        due=date.fromisoformat(p.get("call_due",e["call_due"]))
        require(today<=due and p.get("call_timing_reviewed") is True,"en banc call timing review required")
        require(p["ground"] in {"circuit_conflict","supreme_court_conflict","other_circuit_conflict","exceptional_importance"},"FRAP 40 ground required")
        e.update(status="called",caller=caller,called_at=now,call_due=due.isoformat(),ground=p["ground"])
    elif kind=="ca9.en_banc_open":
        phase(c,"judgment",require=require)
        e=r["en_banc"];require(e["status"] in {"called","voting"},"call required")
        require(p.get("party_opportunity_completed") is True and p.get("memoranda_completed") is True and p.get("roster_complete") is True,"briefing, memoranda and complete roster review required")
        pool=eligible(s,c,True);require(pool,"no eligible voters")
        if e["status"]=="voting":
            require(pool!=e["electorate"],"no electorate change")
            e.setdefault("abandoned_votes",[]).append({"electorate":e["electorate"],"votes":e["votes"],"due":e["vote_due"]})
        due=date.fromisoformat(p["vote_due"]) if p.get("vote_due") else date_due(today,7,r["holidays"])
        require(due>=today,"invalid vote deadline")
        e.update(status="voting",electorate=pool,votes={},vote_due=due.isoformat(),opened_at=now)
    elif kind=="ca9.en_banc_vote":
        phase(c,"judgment",require=require)
        e=r["en_banc"];require(e["status"]=="voting" and e["electorate"]==eligible(s,c,True),"electorate changed; reopen vote")
        require(p["judge_id"] in e["electorate"] and type(p["vote"]) is bool and today<=date.fromisoformat(e["vote_due"]),"invalid/late vote")
        e["votes"][p["judge_id"]]=p["vote"]
    elif kind=="ca9.en_banc_tally":
        phase(c,"judgment",require=require)
        e=r["en_banc"];require(e["status"]=="voting" and e["electorate"]==eligible(s,c,True),"electorate changed or vote inactive")
        require(today>date.fromisoformat(e["vote_due"]),"voting period not expired")
        yes=sum(e["votes"].values());grant=yes>len(e["electorate"])/2
        require(not any(q["panel"]=="pending" for q in r["petitions"].values()),"resolve panel petitions before tally")
        doc(s,c,p,"order_document_id",require,judge_document)
        e.update(status="granted" if grant else "denied",yes=yes,no=len(e["electorate"])-yes,tallied_at=now)
        for q in r["petitions"].values():
            if q["en_banc"]=="pending":q["en_banc"]="granted" if grant else "denied"
        if grant:
            # Vacate immediately upon grant order; keep judgment/review snapshot until draw.
            for o in s["opinions"].values():
                if o["case_id"]==c["id"] and o.get("panel_epoch")==c["panel_epoch"] and o["status"]=="issued":
                    o.update(status="vacated",vacated_at=now,vacatur_reason="en_banc_granted")
                    for pr in s["precedents"].values():
                        if pr["opinion_id"]==o["id"]:pr.update(previous_authority_status=pr["authority_status"],authority_status="nonprecedential",vacated_at=now)
            c["judgment"]["status"]="vacated";c["phase"]="en_banc_pending"
        else:r["denials"].append(today.isoformat())
    elif kind=="ca9.en_banc_draw":
        phase(c,"en_banc_pending",require=require)
        require(r["en_banc"]["status"]=="granted" and p.get("clerk_draw_witnessed") is True,"witnessed clerk draw required")
        pool=eligible(s,c)
        for j in p.get("senior_elections",[]):
            require(j in c["assigned_judges"] and j not in c["excluded_judges"] and member(s["people"][j]) and s["people"][j]["judicial_status"]=="senior_circuit","ineligible senior election")
            if j not in pool:pool.append(j)
        require(len(pool)>=11,"insufficient eligible en banc judges")
        require(isinstance(p["seed"],str) and len(p["seed"])>=8,"record draw seed")
        chiefs=[j for j in pool if active(s["people"][j]) and s["people"][j].get("chief_judge") is True]
        require(len(chiefs)<=1,"multiple chiefs")
        ranked=draw(p["seed"],[j for j in pool if j not in chiefs],c["id"]+"en_banc")
        panel=chiefs+ranked[:11-len(chiefs)]
        c["en_banc_alternates"]=ranked[11-len(chiefs):]
        c["en_banc_draw"]={"seed":p["seed"],"pool":sorted(pool),"panel":panel,"alternates":list(c["en_banc_alternates"])}
        archived_round(s,c,now,"en_banc_granted",True)
        set_panel(s,c,panel,"limited_en_banc","Circuit Rule 40-3",now,require);c["phase"]="merits"
    elif kind=="ca9.en_banc_clear":
        phase(c,"judgment",require=require)
        e=r["en_banc"];require(e["status"]=="open" and p.get("all_notice_call_periods_checked") is True,"coordinator clearance required")
        require(today>=date.fromisoformat(e["call_due"]) and today>date.fromisoformat(r["petition_due"]),"call period not expired")
        if today==date.fromisoformat(e["call_due"]):require(p.get("same_day_call_window_closed") is True,"coordinator must confirm actual call window closed")
        require(not any(q["panel"]=="pending" for q in r["petitions"].values()),"panel petition pending")
        pending=[q for q in r["petitions"].values() if q["en_banc"]=="pending"]
        if pending:
            doc(s,c,p,"order_document_id",require,judge_document)
            for q in pending:q["en_banc"]="denied"
            r["denials"].append(today.isoformat())
        e["status"]="cleared"
    elif kind=="ca9.stay_file":
        phase(c,"judgment",require=require)
        require(not r["stay"] or r["stay"]["status"] in {"denied","ended"},"stay already pending or active")
        r["stay"]={"status":"pending","document_id":doc(s,c,p,"motion_document_id",require,judge_document)}
    elif kind=="ca9.stay_decide":
        phase(c,"judgment",require=require)
        stay=r["stay"];require(stay and stay["status"]=="pending" and type(p["grant"]) is bool,"no pending stay")
        stay["order"]=doc(s,c,p,"order_document_id",require,judge_document)
        if p["grant"]:
            require(p.get("substantial_question") and p.get("good_cause"),"FRAP 41(d) findings required")
            until=date.fromisoformat(p["until"]);require(today<=until<=today+timedelta(days=90),"ordinary stay up to 90 days")
            stay.update(status="active",until=until.isoformat())
        else:stay["status"]="denied";r["denials"].append(today.isoformat())
    elif kind=="ca9.stay_end":
        phase(c,"judgment",require=require)
        stay=r["stay"];require(stay and stay["status"]=="active","no active stay")
        require(p["reason"] in {"expired","court_order","certiorari_denied"},"invalid stay end")
        if p["reason"]=="expired":require(today>date.fromisoformat(stay["until"]) and p.get("no_extension_or_cert_notice") is True,"stay may continue")
        else:doc(s,c,p,"order_document_id",require,judge_document)
        stay.update(status="ended",reason=p["reason"])
    elif kind=="ca9.mandate":
        phase(c,"judgment",require=require)
        require(r["en_banc"]["status"] in {"cleared","denied"} and not any("pending" in (q["panel"],q["en_banc"]) for q in r["petitions"].values()),"review pending")
        require(not r["stay"] or r["stay"]["status"] in {"denied","ended"},"mandate stayed or motion pending")
        anchor=max([r["petition_due"]]+r["denials"])
        due=date_due(date.fromisoformat(anchor),7,r["holidays"])
        immediate=r["stay"] and r["stay"].get("reason")=="certiorari_denied"
        if p.get("timing_order_id"):
            doc(s,c,p,"timing_order_id",require,judge_document)
        else:require(immediate or today>=due,"FRAP 41(b) mandate too early")
        require(p.get("certified_judgment_and_costs_reviewed") is True,"mandate contents review required")
        c["mandate"]={"document_id":doc(s,c,p,"mandate_document_id",require,judge_document),"issued_at":now,"ordinary_due":due.isoformat(),"rule_basis":p["rule_basis"]}
        c.update(phase="mandate_issued",status="closed")
    elif kind=="ca9.mandate_recall":
        phase(c,"mandate_issued",require=require)
        require(p.get("extraordinary_circumstances") and p.get("authority_reviewed") is True,"exceptional recall review required")
        old=deepcopy(c["mandate"]);old.update(recalled_at=now,recall_order=doc(s,c,p,"order_document_id",require,judge_document))
        c.setdefault("mandate_history",[]).append(old);c["mandate"]=None
        c.update(phase="judgment",status="pending")
        # Recall is recorded; further review requires separate legal decision.
        c["review"]["en_banc"]["status"]="open"
