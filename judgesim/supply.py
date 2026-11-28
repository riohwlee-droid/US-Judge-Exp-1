"""Creator-side production queue. Official cases remain in the checkpoint reducer."""
from copy import deepcopy
from datetime import date
from pathlib import Path
from collections import Counter
from .case_factory import STAGES, TRACKS, DISTRICTS, check_release, compile_package, canonical, no_answers, key, at, need, safe
from .storage import read_json, write_json, sha, verify
from .engine import moment

OPEN={"queued","working","rework","reviewed"}
FINAL={"sealed","cancelled"}
def new_ledger():
    return {"schema_version":1,"next_serial":1,"jobs":{},"receipts":{}}
def policy_check(p):
    need(p["schema_version"]==1 and p["court_id"]=="CA9","supply policy")
    date.fromisoformat(p["provisional_cutoff"])
    need(all(type(p[k]) is int for k in ("low_watermark","target_stock","max_open_jobs","max_intake_per_turn")),"integer limits")
    need(0<=p["low_watermark"]<p["target_stock"]<=20 and 1<=p["max_open_jobs"]<=20 and 1<=p["max_intake_per_turn"]<=5,"invalid stock policy")
    need(set(p["track_weights"])==set(TRACKS) and all(type(v) is int and v>0 for v in p["track_weights"].values()),"invalid track weights")
    need(set(p["district_rotation"])==DISTRICTS and len(p["district_rotation"])==len(DISTRICTS),"invalid district rotation")
def history(job,action,note,revision):
    job["history"].append({"action":action,"note":note,"revision":revision})
def make_job(ledger,p,cutoff,revision,track=None,district=None,manual=False):
    n=ledger["next_serial"];ledger["next_serial"]+=1
    cid=f"CA9-SUP-{n:06d}"
    need(cid not in ledger["jobs"],"duplicate supply serial")
    # Stable weighted selection; no legal issue or outcome selected here.
    weights=p["track_weights"];pick=int(canonical([p["seed"],n])[:16],16)%sum(weights.values())
    selected=None
    for t,w in sorted(weights.items()):
        if pick<w:selected=t;break
        pick-=w
    track=track or selected;district=district or p["district_rotation"][(n-1)%len(p["district_rotation"])]
    need(track in TRACKS and district in DISTRICTS,"unsupported factory request")
    j={"id":cid,"version":"v1","track":track,"origin_district":district,"legal_cutoff":cutoff,"status":"queued","stage_index":-1,"attempt":0,"blueprint_path":f"factory/{cid}/v1/blueprint.json","release_path":None,"release_digest":None,"record_as_of":None,"requested_revision":revision,"history":[]}
    history(j,"request","manual creator request" if manual else "automatic stock replenishment",revision)
    ledger["jobs"][cid]=j
    return j
def validate_release_job(root,j,r,path):
    need(r["case_id"]==j["id"] and r["version"]==j["version"] and r["legal_cutoff"]==j["legal_cutoff"],"release/job identity or cutoff mismatch")
    b=read_json(safe(root,r["blueprint_path"]))
    need(b["track"]==j["track"] and b["origin_district"]==j["origin_district"] and r["blueprint_path"]==j["blueprint_path"],"release/job scope mismatch")
    if j["status"]=="sealed":
        need(j["release_path"]==path and j["release_digest"]==canonical(r),"sealed job changed")
def import_seals(root,ledger,p,revision):
    for dest in sorted((root/"factory").glob("*/*/release.json")):
        path=dest.relative_to(root).as_posix()
        r=check_release(root,path);cid=r["case_id"];j=ledger["jobs"].get(cid)
        if j is None:
            # Explicit one-time migration only; random external releases are never inventory.
            if path!=p["legacy_release"]:continue
            b=read_json(safe(root,r["blueprint_path"]))
            j={"id":cid,"version":r["version"],"track":b["track"],"origin_district":b["origin_district"],"legal_cutoff":r["legal_cutoff"],"status":"reviewed","stage_index":len(STAGES)-1,"attempt":1,"blueprint_path":r["blueprint_path"],"release_path":None,"release_digest":None,"record_as_of":None,"requested_revision":revision,"history":[]}
            ledger["jobs"][cid]=j
            history(j,"import","verified legacy release",revision)
        need(j["status"]!="cancelled","cancelled job has a release; review required")
        validate_release_job(root,j,r,path)
        if j["status"]!="sealed":
            j.update(status="sealed",stage_index=len(STAGES)-1,release_path=path,release_digest=canonical(r),record_as_of=r["record_as_of"])
            history(j,"seal","factory release verified",revision)
def eligible(j,s,cutoff):
    if j["status"]!="sealed" or j["id"] in s["cases"] or j["legal_cutoff"]!=cutoff:return False
    now=s["campaign"].get("game_time")
    return now is None or at(j["record_as_of"])<=moment(now)
def inventory(ledger,s,p):
    cutoff=s["campaign"].get("legal_cutoff") or p["provisional_cutoff"]
    counts=Counter()
    for j in ledger["jobs"].values():
        c=s["cases"].get(j["id"])
        if c:
            need(j["status"]=="sealed" and c["factory_release"]["digest"]==j["release_digest"],"admitted job/release mismatch")
            counts["closed" if c["status"]=="closed" else "registered_unassigned" if c["phase"]=="unassigned" else "assigned"]+=1
        elif j["status"]=="sealed":
            counts["ready" if eligible(j,s,cutoff) else "blocked_date_or_cutoff"]+=1
        elif j["status"] in OPEN:
            counts[j["status"] if j["legal_cutoff"]==cutoff else "blocked_date_or_cutoff"]+=1
        else:counts["cancelled"]+=1
    return {"cutoff":cutoff,**{k:counts[k] for k in ("ready","registered_unassigned","assigned","closed","queued","working","rework","reviewed","blocked_date_or_cutoff","cancelled")}}
def replenish(ledger,s,p,revision):
    x=inventory(ledger,s,p)
    # Unassigned admitted cases still count as available supply; open failed jobs count as
    # pipeline work, to avoid infinite demand while a producer is blocked.
    available=x["ready"]+x["registered_unassigned"]
    open_count=sum(x[k] for k in OPEN)
    if available<=p["low_watermark"] or available+open_count<p["target_stock"]:
        n=min(max(0,p["target_stock"]-available-open_count),max(0,p["max_open_jobs"]-open_count))
        for _ in range(n):make_job(ledger,p,x["cutoff"],revision)
def process_command(root,ledger,p,s,cmd,revision):
    no_answers(cmd);need(cmd["schema_version"]==1,"supply request version")
    action=cmd["action"]
    if action=="request":
        need(sum(j["status"] in OPEN and j["legal_cutoff"]==(s["campaign"].get("legal_cutoff") or p["provisional_cutoff"]) for j in ledger["jobs"].values())<p["max_open_jobs"],"production capacity full")
        return make_job(ledger,p,s["campaign"].get("legal_cutoff") or p["provisional_cutoff"],revision,cmd.get("track"),cmd.get("origin_district"),True)["id"]
    j=ledger["jobs"][key(cmd["job_id"])]
    expected=cmd["expected_status"];need(expected==j["status"],"stale production status")
    need(j["status"] in OPEN,"sealed/cancelled job immutable")
    if action=="start":
        need(j["status"]=="queued","only queued job may start");j["status"]="working";j["attempt"]+=1
    elif action=="retry":
        need(j["status"]=="rework","only failed job may retry");j["status"]="working";j["attempt"]+=1
    elif action=="progress":
        need(j["status"]=="working" and isinstance(cmd.get("note"),str) and cmd["note"].strip(),"working progress requires note")
    elif action=="cancel":
        need(isinstance(cmd.get("note"),str) and cmd["note"].strip(),"cancellation reason required");j["status"]="cancelled"
    elif action in {"advance","seal"}:
        need(j["status"]==("working" if action=="advance" else "reviewed"),"wrong stage for validation")
        stage=STAGES[j["stage_index"]+1] if action=="advance" and j["stage_index"]+1<len(STAGES) else "review"
        need(cmd.get("stage")==stage,"unexpected validation stage")
        try:
            b=read_json(safe(root,j["blueprint_path"]))
            need(b["case_id"]==j["id"] and b["version"]==j["version"] and b["track"]==j["track"] and b["origin_district"]==j["origin_district"] and b["legal_cutoff"]==j["legal_cutoff"],"blueprint scope mismatch")
            r=compile_package(root,j["blueprint_path"],stage=stage)
            if action=="advance":
                j["stage_index"]=STAGES.index(stage)
                j["status"]="reviewed" if stage=="review" else "working"
            else:
                path=str(Path(j["blueprint_path"]).with_name("release.json"))
                dest=safe(root,path);need(not dest.exists(),"release already exists")
                # Compiler returns the actual seal, not a caller-supplied digest.
                validate_release_job(root,j,r,path)
                write_json(dest,r)
                try:validate_release_job(root,j,check_release(root,path),path)
                except Exception:
                    dest.unlink()
                    raise
                j.update(status="sealed",release_path=path,release_digest=canonical(r),record_as_of=r["record_as_of"])
        except (ValueError,KeyError,TypeError,OSError,IndexError) as exc:
            j["status"]="rework"
            if action=="seal":j["stage_index"]=len(STAGES)-2
            history(j,"validation_failed",stage+": "+str(exc)[:1000],revision)
            return j["id"]
    else:raise ValueError("unknown supply action")
    history(j,action,str(cmd.get("note") or cmd.get("stage") or "")[:1000],revision)
    return j["id"]
def sync(root):
    root=Path(root);p=read_json(root/"supply/policy.json");policy_check(p)
    s=verify(root);pointer=read_json(root/"CURRENT.json");rev=pointer["revision"]
    dest=root/"supply/STATE.json"
    ledger=read_json(dest) if dest.exists() else new_ledger()
    need(ledger["schema_version"]==1,"supply ledger version")
    import_seals(root,ledger,p,rev)
    for q in sorted((root/"supply/requests").glob("*.json")):
        rid=key(q.stem);d=sha(q);old=ledger["receipts"].get(rid)
        if old:
            need(old["request_sha256"]==d,"processed supply request modified")
            need(read_json(root/"supply/receipts"/(rid+".json"))==old,"supply receipt changed")
            continue
        cmd=read_json(q);receipt={"request_id":rid,"request_sha256":d}
        trial=deepcopy(ledger)
        try:
            need(cmd["request_id"]==rid,"request ID mismatch")
            jid=process_command(root,trial,p,s,cmd,rev)
            ledger=trial;job=ledger["jobs"][jid]
            receipt.update(status="rework" if job["status"]=="rework" else "accepted",job_id=jid,job_status=job["status"],stage_index=job["stage_index"])
            if job["status"]=="rework":receipt["reason"]=job["history"][-1]["note"]
        except (ValueError,KeyError,TypeError,OSError,IndexError) as exc:receipt.update(status="rejected",reason=str(exc)[:1000])
        ledger["receipts"][rid]=receipt
        write_json(root/"supply/receipts"/(rid+".json"),receipt)
    import_seals(root,ledger,p,rev)
    for j in ledger["jobs"].values():
        if j["status"]=="sealed":check_release(root,j["release_path"],j["release_digest"])
    replenish(ledger,s,p,rev)
    ledger["as_of_checkpoint"]=pointer["checkpoint"];ledger["as_of_revision"]=rev
    write_json(dest,ledger)
    public={"schema_version":1,"checkpoint":pointer["checkpoint"],"revision":rev,"campaign_status":s["campaign"]["status"],"inventory":inventory(ledger,s,p),"target_stock":p["target_stock"],"low_watermark":p["low_watermark"]}
    write_json(root/"supply/PUBLIC.json",public)
    return public
def candidates(root,state):
    root=Path(root);p=read_json(root/"supply/policy.json");policy_check(p)
    ledger=read_json(root/"supply/STATE.json")
    cutoff=state["campaign"]["legal_cutoff"]
    result=[]
    for j in ledger["jobs"].values():
        if eligible(j,state,cutoff):
            r=check_release(root,j["release_path"],j["release_digest"])
            validate_release_job(root,j,r,j["release_path"])
            result.append(j)
    return sorted(result,key=lambda j:(at(j["record_as_of"]),j["id"]))
def intake_plan(root,state,payload):
    """Reviewed clerk inputs only; select oldest eligible, never choose player panel."""
    need(state["campaign"]["status"]=="active" and state["campaign"].get("organization"),"install roster before supply intake")
    p=read_json(Path(root)/"supply/policy.json")
    limit=payload.get("limit",p["max_intake_per_turn"])
    need(type(limit) is int and 1<=limit<=p["max_intake_per_turn"],"intake batch limit")
    reviews=payload["reviews"];need(isinstance(reviews,dict),"case-specific clerk reviews required")
    result=[]
    for j in candidates(root,state):
        if len(result)>=limit:break
        rv=reviews.get(j["id"])
        # Do not leapfrog an older case without a documented reason.
        if not rv:break
        if rv.get("defer_reason"):
            need(isinstance(rv["defer_reason"],str) and rv["defer_reason"].strip(),"reviewed deferral reason");continue
        need(rv.get("conflict_review_completed") is True and rv.get("jurisdiction_review_completed") is True and rv.get("review_note"),"case-specific review incomplete")
        result.append(j)
    return result

def calendar_events(root,state,event):
    """Convert a reviewed clerk calendar request to ordinary assignment events.
    Capacity is computed from existing assignments, not reset for each case.
    No special preference for the player. Future months may be calendared."""
    from .engine import apply_batch
    from .storage import profiles
    p=event["payload"];no_answers(p)
    need(state["campaign"]["status"]=="active" and state["campaign"].get("organization"),"active installed organization required")
    policy=read_json(Path(root)/"supply/policy.json")
    reviews=p["reviews"];limit=p.get("limit",policy["max_intake_per_turn"])
    need(type(limit) is int and 1<=limit<=policy["max_intake_per_turn"],"calendar batch limit")
    pending=sorted((c for c in state["cases"].values() if c["court_id"]=="CA9" and c["phase"]=="unassigned"),key=lambda c:(at(c["factory_record_as_of"]),c["id"]))
    emitted=[];current=state
    for c in pending:
        if len(emitted)>=limit:break
        rv=reviews.get(c["id"])
        if not rv:break
        if rv.get("defer_reason"):
            need(isinstance(rv["defer_reason"],str) and rv["defer_reason"].strip(),"reviewed deferral reason");continue
        need(rv.get("calendar_review_completed") is True and rv.get("legal_review_completed") is True and rv.get("rule_basis") and rv.get("priority_review"),"clerk calendar review incomplete")
        month=rv["calendar_month"]
        need(isinstance(month,str) and len(month)==7 and date.fromisoformat(month+"-01")>=date.fromisoformat(current["campaign"]["game_time"][:7]+"-01"),"past/invalid calendar month")
        weight=rv["case_weight"]
        need(type(weight) is int and weight>0,"case weight")
        slots=[];seen=set()
        for raw in rv["slots"]:
            slot=deepcopy(raw);sid=key(slot["id"])
            need(sid not in seen,"duplicate calendar slot");seen.add(sid)
            if slot["location"]!=c["calendar_location"] or slot["month"]!=month:continue
            total=slot.pop("total_weight")
            need(type(total) is int and total>0,"reviewed total slot capacity required")
            used=0
            for old in current["cases"].values():
                a=old.get("assignment",{})
                if a.get("slot_id")==sid and a.get("calendar_month")==month and old["calendar_location"]==slot["location"]:
                    if a.get("slot_total_weight") is not None:
                        need(a["slot_total_weight"]==total and a["slot_judges"]==slot["judges"],"calendar slot definition changed")
                    used+=a["weight"]
            slot["remaining_weight"]=total-used;slot["total_weight"]=total
            if slot["remaining_weight"]>=weight:slots.append(slot)
        if not slots:break
        payload={"case_id":c["id"],"seed":canonical([event["id"],c["id"],month]),"calendar_month":month,"case_weight":weight,"slots":slots,"calendar_review_completed":True,"legal_review_completed":True,"rule_basis":rv["rule_basis"],"priority_review":rv["priority_review"],"supply_calendar":True}
        actual={"id":key(event["id"]+"-A"+str(len(emitted)+1)),"type":"ca9.assign","payload":payload}
        current=apply_batch(current,[actual],profiles(root));emitted.append(actual)
    need(emitted,"no reviewed eligible unassigned case/calendar slot")
    return emitted,current

def notices(state):
    """Only actual assigned player cases; derived from the immutable assignment event."""
    player=(state["campaign"].get("player") or {}).get("id")
    result=[]
    if not player:return result
    for c in state["cases"].values():
        a=c.get("assignment")
        if a and player in c["assigned_judges"] and c["status"]!="closed":
            result.append({"id":"ASSIGN-"+c["id"],"case_id":c["id"],"title":c.get("title",c["id"]),"at":a["at"],"calendar_month":a["calendar_month"],"panel":list(c["assigned_judges"]),"message":"A case has been assigned to your panel. The appellate briefs and excerpts of record are available in your chambers docket."})
    return sorted(result,key=lambda n:(n["at"],n["id"]))
