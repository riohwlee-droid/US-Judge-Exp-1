"""Fictional CA9 organization installation and role/interaction guards."""
from copy import deepcopy
from datetime import date

def nonblank(v): return isinstance(v,str) and bool(v.strip())
def age(b,on):
    return on.year-b.year-((on.month,on.day)<(b.month,b.day))
def day(v):return date.fromisoformat(v)

def check_roster(pkg, require):
    require(pkg["fictional"] is True and pkg["schema_version"]==1,"fictional roster v1 required")
    people=pkg["people"]; ids=[p["id"] for p in people]
    require(len(ids)==len(set(ids)) and len({p["name"] for p in people})==len(ids),"duplicate roster ID/name")
    by={p["id"]:p for p in people}; player=pkg["player_slot"]["id"]
    require(player not in by,"player slot must be empty")
    seats=pkg["seats"];require(len(seats)==29 and len({x["id"] for x in seats})==29,"CA9 29 statutory seats required")
    active=[p for p in people if p.get("judicial_status")=="active_circuit"]
    senior=[p for p in people if p.get("judicial_status")=="senior_circuit"]
    require(len(active)==28 and len([x for x in seats if x["occupant_id"] is None and x["status"]=="reserved_player"])==1,"28 NPCs plus player seat required")
    require({x["occupant_id"] for x in seats if x["occupant_id"]}=={p["id"] for p in active},"seat mismatch")
    require(all(x["status"]=="occupied" and by[x["occupant_id"]]["seat_id"]==x["id"] for x in seats if x["occupant_id"]),"seat mapping invalid")
    require(next(x["id"] for x in seats if not x["occupant_id"])==pkg["player_slot"]["seat_id"],"player seat mismatch")
    require([p["seniority_rank"] for p in sorted(active,key=lambda x:x["commission_date"])]==list(range(1,29)),"commission seniority mismatch")
    require(len({p["commission_date"] for p in active})==28,"commission dates tied")
    chiefs=[p for p in active if p["chief_judge"]]
    require(len(chiefs)==1,"one chief required")
    chief=chiefs[0]; start=day(chief["chief_since"]); baseline=day(pkg["baseline_date"])
    require(day(chief["commission_date"])<=start and age(day(chief["birth_date"]),start)<=64 and age(day(chief["birth_date"]),baseline)<70 and (start-day(chief["commission_date"])).days>=365 and not chief["previous_chief"],"chief eligibility")
    eligible=[p for p in active if day(p["commission_date"])<=start and (start-day(p["commission_date"])).days>=365 and age(day(p["birth_date"]),start)<=64 and not p["previous_chief"]]
    require(min(eligible,key=lambda p:p["commission_date"])["id"]==chief["id"],"chief selection seniority mismatch")
    for p in active+senior:
        require(p["fictional"] is True and p["role"]=="judge" and p["court_id"]=="CA9" and p["active"] is True,"invalid judge")
        require(day(p["birth_date"])<day(p["commission_date"])<=baseline and age(day(p["birth_date"]),day(p["commission_date"]))>=25,"fictional career chronology")
        require(all(nonblank(p["judicial_profile"].get(k)) for k in ("statutory_method","constitutional_method","holding_scope","conference_style","focus","writing_style","change_condition")),"incomplete judicial profile")
        require(p["prior_opinion_ids"]==[],"no invented prior opinion anchors")
    for p in senior:
        sd=day(p["senior_since"]);a=age(day(p["birth_date"]),sd);years=age(day(p["commission_date"]),sd)
        require(p["seat_id"] is None and not p["chief_judge"] and sd<=baseline and a>=65 and years>=10 and a+years>=80,"senior status eligibility")
    chambers=pkg["chambers"];units=pkg["units"]
    require(len({x["id"] for x in chambers+units})==len(chambers)+len(units),"duplicate organization ID")
    require({x["judge_id"] for x in chambers}=={p["id"] for p in active+senior}|{player},"chambers mismatch")
    assigned=[]
    for ch in chambers:
        require(ch["planned"]==(ch["judge_id"]==player),"chambers status mismatch")
        for pid in ch["staff_ids"]:
            p=by[pid];require(p["role"] in {"law_clerk","staff"} and p["chambers_id"]==ch["id"] and p["supervisor_id"]==ch["judge_id"],"staff reporting mismatch")
            require(p["active"] is not ch["planned"],"planned chamber activation mismatch")
            assigned.append(pid)
    for u in units:
        require(u["parent_id"] is None or any(v["id"]==u["parent_id"] for v in units),"unknown unit parent")
        for pid in u["staff_ids"]:
            p=by[pid];require(p["role"]=="staff" and p["unit_id"]==u["id"] and (p["supervisor_id"] is None or p["supervisor_id"] in u["staff_ids"]),"invalid unit staff")
            assigned.append(pid)
    require(len(assigned)==len(set(assigned)) and set(assigned)=={p["id"] for p in people if p["role"]!="judge"},"unassigned or duplicate staff")
    require(all(p["fictional"] is True and p["court_id"]=="CA9" for p in people),"nonfictional or foreign roster")

def install(s,p,require,moment,digest):
    c=s["campaign"];pkg=p["roster"];player=deepcopy(c["player"])
    require(c["court_id"]=="CA9" and not s["people"] and not s["cases"] and not c.get("organization"),"install once before case registration")
    require(p.get("user_confirmed") is True and p.get("roster_digest")==digest(pkg),"roster confirmation/digest required")
    check_roster(pkg,require)
    require(player["id"]==pkg["player_slot"]["id"] and all(nonblank(player.get(k)) for k in pkg["player_slot"]["required"]),"player details missing")
    now=moment(c["game_time"]).date(); commissioned=day(player["commission_date"])
    require(day(pkg["baseline_date"])<=now and day(player["birth_date"])<commissioned<=now and age(day(player["birth_date"]),commissioned)>=25,"player chronology invalid")
    active=[x for x in pkg["people"] if x.get("judicial_status")=="active_circuit"]
    require(commissioned>max(day(x["commission_date"]) for x in active),"player reserved junior seat requires latest commission")
    chief=next(x for x in active if x["chief_judge"])
    require(age(day(chief["birth_date"]),now)<70 and age(day(chief["chief_since"]),now)<7,"chief term review needed")
    player.update(fictional=True,role="judge",active=True,court_id="CA9",judicial_status="active_circuit",seat_id=pkg["player_slot"]["seat_id"],seniority_rank=29,chief_judge=False,prior_opinion_ids=[],relationships={},interaction_log=[],judicial_profile={"controlled_by":"user","no_predetermined_vote":True})
    require(player["name"] not in {x["name"] for x in pkg["people"]},"player name duplicates NPC")
    s["people"].update({x["id"]:deepcopy(x) for x in pkg["people"]});s["people"][player["id"]]=player
    org={k:deepcopy(pkg[k]) for k in ("seats","units","chambers")}
    org.update(roster_id=pkg["id"],roster_digest=p["roster_digest"],installed_at=c["game_time"])
    for seat in org["seats"]:
        if seat["id"]==player["seat_id"]:seat.update(occupant_id=player["id"],status="occupied")
    for ch in org["chambers"]:
        if ch["judge_id"]==player["id"]:
            ch.update(planned=False,city=player["chambers_city"])
            for j in ch["staff_ids"]:s["people"][j]["active"]=True
    c["organization"]=org

def validate_installed(s,require):
    org=s["campaign"].get("organization")
    if not org:return
    people=s["people"]
    seats=org["seats"];require(len(seats)==29 and len({x["id"] for x in seats})==29,"invalid active seats")
    occupants={x["occupant_id"] for x in seats}
    require(None not in occupants and len(occupants)==29,"duplicate/missing seat occupant")
    require(occupants=={j for j,p in people.items() if p.get("court_id")=="CA9" and p.get("judicial_status")=="active_circuit" and p["active"]},"active seat roster mismatch")
    require(sum(people[j].get("chief_judge",False) for j in occupants)==1,"chief mismatch")
    for ch in org["chambers"]:
        require(ch["judge_id"] in people and not ch["planned"],"uninstalled chamber")
        require(all(people[j]["supervisor_id"]==ch["judge_id"] for j in ch["staff_ids"]),"chamber mismatch")

def task_guard(s,p,require):
    c=s["cases"][p["case_id"]];actor=p.get("assigning_judge_id");target=s["people"][p["assignee_id"]]
    require(actor in c["assigned_judges"] and actor in s["people"] and s["people"][actor]["active"],"assigning judge must be current panel member")
    require(p.get("task_kind") in {"research","bench_memo","draft_assistance","record_check","administration"},"task type required; no delegation of vote")
    if target.get("chambers_id"):
        require(target["supervisor_id"]==actor,"cannot direct another judge's chambers")
        require(target["role"]=="law_clerk" or p["task_kind"]=="administration","judicial assistant administrative only")
    else:
        require(target.get("unit_id") in {"U-CLERK","U-STAFF-ATTORNEYS","U-LIBRARY","U-COMMISSIONER","U-ENBANC","U-IT"} and p.get("unit_referral_reviewed") is True,"shared unit referral requires authority review")
        if target.get("unit_id") in {"U-CLERK","U-ENBANC","U-IT"}:require(p["task_kind"]=="administration","administrative referral only")
    require(c["phase"]!="mandate_issued","case closed")
    require(target["role"] in {"staff","law_clerk"},"only staff may receive delegated work")

def initial_view(s,p,require):
    c=s["cases"][p["case_id"]];j=p["judge_id"];d=s["documents"][p["document_id"]]
    require(c["phase"]=="merits" and j in c["assigned_judges"] and j!=s["campaign"]["player"]["id"],"NPC current panel only")
    require(d["case_id"]==c["id"] and d["access"]=="npc_private" and d["status"]=="internal","private preliminary memo required")
    require(nonblank(p.get("disposition")),"independent disposition required")
    key=str(c["panel_epoch"]); views=c.setdefault("independent_views",{}).setdefault(key,{})
    require(j not in views and not any(x.get("panel_epoch")==c["panel_epoch"] for x in c.get("conferences",[])),"initial view already recorded or conference occurred")
    views[j]={"document_id":d["id"],"disposition":p["disposition"],"recorded_at":s["campaign"]["game_time"]}

def conference_guard(s,c,require):
    player=s["campaign"]["player"]["id"]
    views=c.get("independent_views",{}).get(str(c["panel_epoch"]),{})
    require(set(views)==set(c["assigned_judges"])-{player},"record independent NPC initial views before conference")

def interaction(s,p,require,judge_document):
    actor=p["actor_id"];other=p["other_id"];require(actor!=other and actor in s["people"] and other in s["people"],"unknown interaction participants")
    d=judge_document(s,p["document_id"]);c=s["cases"][d["case_id"]]
    require(d["status"]=="internal" and p.get("category") in {"correspondence","revision_request","work_feedback","professional_relationship"},"internal interaction record required")
    require(any(j in c["assigned_judges"] for j in (actor,other)),"interaction requires case panel participant")
    require(nonblank(p.get("summary")),"summary required")
    for a,b in ((actor,other),(other,actor)):
        person=s["people"][a]
        log=person.setdefault("interaction_log",[])
        require(not any(x["document_id"]==d["id"] for x in log),"duplicate interaction")
        log.append({"other_id":b,"document_id":d["id"],"category":p["category"],"at":s["campaign"]["game_time"],"summary":p["summary"]})
        person.setdefault("relationships",{})[b]={"last_interaction":d["id"],"professional_note":p["summary"]}
