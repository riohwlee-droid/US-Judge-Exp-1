"""Deterministic event reducer. This enforces storage/workflow, not legal correctness."""
from copy import deepcopy
from . import ca9, ca9_lifecycle as life, ca9_people as org
from datetime import datetime, timedelta
import hashlib
import json
import re


class Invalid(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise Invalid(message)


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()


def moment(value):
    require(isinstance(value, str), "time must be an ISO string")
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise Invalid("invalid ISO time") from exc
    require(dt.tzinfo is not None, "time requires a UTC offset")
    return dt


def identifier(value):
    require(isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,119}", value),
            "invalid identifier")
    return value


def fresh(table, key):
    identifier(key)
    require(key not in table, f"duplicate identifier: {key}")


def entity(table, key):
    require(key in table, f"unknown entity: {key}")
    return table[key]


def initial_state():
    return {
        "schema_version": 1, "revision": 0,
        "campaign": {"status": "setup_required", "player": None, "court_id": None,
                     "game_time": None, "law_policy": "verified_start_then_branch",
                     "legal_cutoff": None, "scene": "onboarding"},
        "cases": {}, "people": {}, "documents": {}, "tasks": {}, "deadlines": {},
        "opinions": {}, "precedents": {}, "career": [], "applied_events": {}
    }


def court(profiles, key, allow_training):
    c = entity(profiles, key)
    require(c["status"] == "ready" or (allow_training and c["status"] == "training_only"),
            "court is not ready: research is required")
    if c["status"] == "ready":
        require(c.get("source_ids") and c.get("checked_on") and c.get("role") and
                c.get("jurisdiction") and c.get("appeal_route") and
                c.get("appointment") and c.get("staffing") and c.get("rules"),
                "ready court lacks required profile fields")
    return c


def judge_document(state, doc_id):
    doc = entity(state["documents"], doc_id)
    require(doc["access"] == "judge", "document is outside the judge's accessible record")
    return doc


def reference(state, citation):
    doc = judge_document(state, citation["document_id"])
    require(isinstance(citation["page"], int) and not isinstance(citation["page"], bool)
            and 1 <= citation["page"] <= doc["pages"], "nonexistent page")
    return doc


def view(state):
    """Player view excludes world-only/unfiled evidence and NPC private material."""
    result = deepcopy(state)
    result["documents"] = {k: v for k, v in result["documents"].items() if v["access"] == "judge"}
    result.pop("applied_events", None)
    for case in result["cases"].values():
        case.pop("independent_views",None)
    return result


def validate_state(state, profiles, allow_training=False):
    require(set(state) == set(initial_state()), "unexpected/missing state fields")
    require(state["schema_version"] == 1 and type(state["revision"]) is int and state["revision"] >= 0,
            "invalid state version")
    require(len(state["applied_events"]) == state["revision"], "event/revision mismatch")
    campaign = state["campaign"]
    require(campaign["status"] in {"setup_required", "active", "paused", "retired"}, "bad campaign status")
    if campaign["status"] != "setup_required":
        court(profiles, campaign["court_id"], allow_training)
        moment(campaign["game_time"])
        require(campaign["player"] and campaign["legal_cutoff"], "missing player or law cutoff")
    else:
        require(not state["cases"] and campaign["player"] is None and campaign["game_time"] is None,
                "unconfigured campaign has live data")
    for table_name in ("cases", "people", "documents", "tasks", "deadlines", "opinions", "precedents"):
        require(isinstance(state[table_name], dict), f"{table_name} must be a mapping")
        for key, obj in state[table_name].items():
            identifier(key)
            require(obj["id"] == key, "entity identifier mismatch")
    org.validate_installed(state,require)
    for case in state["cases"].values():
        profile = court(profiles, case["court_id"], allow_training)
        require(case["matter_type"] in profile["matter_types"], "court lacks matter capability")
        require(case["record_status"] in {"preparing", "complete"}, "bad record status")
        for person in case["assigned_judges"]:
            require(entity(state["people"], person)["role"] == "judge", "panel member is not a judge")
        if case["court_id"] == "CA9":
            life.validate(state, case, require)
        for hearing in case["hearings"].values():
            require(hearing["kind"] in profile["hearing_kinds"] and
                    hearing["status"] in {"scheduled", "in_progress", "completed", "cancelled"}, "bad hearing")
    for doc in state["documents"].values():
        entity(state["cases"], doc["case_id"])
        require(doc["access"] in {"judge", "world_only", "npc_private"}, "bad document access")
        require(doc["status"] in {"filed", "internal", "unfiled"}, "bad filing status")
        require(not (doc["access"] == "judge" and doc["status"] == "unfiled"), "unfiled evidence leaked")
        require(type(doc["pages"]) is int and doc["pages"] > 0, "invalid page count")
        require(re.fullmatch(r"[a-f0-9]{64}", doc["sha256"]) is not None, "invalid document hash")
        require(doc["path"].startswith("records/") or (allow_training and doc["path"].startswith("examples/")),
                "invalid record path")
    for task in state["tasks"].values():
        entity(state["cases"], task["case_id"])
        entity(state["people"], task["assignee_id"])
        moment(task["due_at"])
        if task["status"] == "completed":
            judge_document(state, task["output_document_id"])
    for deadline in state["deadlines"].values():
        entity(state["cases"], deadline["case_id"])
        moment(deadline["due_at"])
        require(deadline["basis"], "deadline needs its order/rule basis")
    for opinion in state["opinions"].values():
        case = entity(state["cases"], opinion["case_id"])
        doc = judge_document(state, opinion["document_id"])
        require(doc["case_id"] == case["id"], "opinion document belongs to another case")
        require(opinion["parts"] and len(set(opinion["parts"])) == len(opinion["parts"]), "invalid opinion parts")
        panel = opinion.get("panel_judges", case["assigned_judges"])
        if case["court_id"] == "CA9":
            require(any(h["epoch"]==opinion.get("panel_epoch") and h["judges"]==panel for h in case["panel_history"]), "opinion panel snapshot invalid")
        require(opinion["author_id"] in panel, "author is outside panel")
        for judge_id, position in opinion["positions"].items():
            require(judge_id in panel, "voter is outside panel")
            require(set(position["joined_parts"]) <= set(opinion["parts"]), "unknown joined part")
            require(position["stance"] in {"join", "concur", "dissent", "pending"}, "bad position")
    for precedent in state["precedents"].values():
        entity(state["opinions"], precedent["opinion_id"])
        require(precedent["origin"] == "simulation" and precedent["authority_status"], "invalid precedent")


def apply_batch(state, events, profiles, allow_training=False):
    """All-or-nothing in memory; save publication is handled by the checkpoint protocol."""
    result = deepcopy(state)
    for event in events:
        identifier(event["id"])
        signature = digest(event)
        previous = result["applied_events"].get(event["id"])
        if previous is not None:
            require(previous == signature, "event ID reused with different content")
            continue
        kind, p = event["type"], event["payload"]
        campaign = result["campaign"]
        if kind == "system.check":
            require(p == {"purpose": "connection_check"}, "invalid system check")
        elif kind == "campaign.configure":
            require(campaign["status"] == "setup_required", "campaign already configured")
            require(p.get("user_confirmed") is True, "starting choices require user input")
            court(profiles, p["court_id"], allow_training)
            moment(p["game_time"])
            require(p["player"] and p["legal_cutoff"], "missing setup choices")
            campaign.update(status="active", player=deepcopy(p["player"]), court_id=p["court_id"],
                            game_time=p["game_time"], legal_cutoff=p["legal_cutoff"], scene="chambers")
        else:
            require(campaign["status"] == "active", "campaign is not active")
            if kind == "ca9.organization_install":
                org.install(result,p,require,moment,digest)
            elif kind == "ca9.independent_view":
                require(campaign.get("organization"),"CA9 roster required")
                org.initial_view(result,p,require)
            elif kind == "ca9.interaction":
                require(campaign.get("organization"),"CA9 roster required")
                org.interaction(result,p,require,judge_document)
            elif kind == "person.register":
                obj = deepcopy(p["person"])
                fresh(result["people"], obj["id"])
                require(obj["role"] in {"judge", "law_clerk", "staff", "counsel", "witness", "party"}, "bad role")
                require(obj.get("fictional") is True, "simulation characters must be fictional")
                if campaign.get("organization"):
                    require(obj["role"] in {"counsel","witness","party"}, "court roster changes require dedicated reviewed personnel process")
                result["people"][obj["id"]] = obj
            elif kind == "case.register":
                obj = deepcopy(p["case"])
                fresh(result["cases"], obj["id"])
                require(obj["court_id"] == campaign["court_id"], "case is not assigned to current court")
                profile = court(profiles, obj["court_id"], allow_training)
                require(obj["matter_type"] in profile["matter_types"], "wrong case for court")
                require(obj.get("fictional") is True, "case must be fictional")
                require(obj.get("record_status") == "complete", "full initial record must be prepared before play")
                obj.update(hearings={}, writing_status="not_started", status="pending")
                if obj["court_id"] == "CA9":
                    require(allow_training or campaign.get("organization"),"install CA9 organization before registering cases")
                    life.init_case(obj, require)
                result["cases"][obj["id"]] = obj
            elif kind == "document.register":
                obj = deepcopy(p["document"])
                fresh(result["documents"], obj["id"])
                if obj.get("supersedes"):
                    old = entity(result["documents"], obj["supersedes"])
                    require(old["case_id"] == obj["case_id"], "correction crosses cases")
                result["documents"][obj["id"]] = obj
            elif kind in life.EVENTS:
                life.handle(result, kind, p, campaign["game_time"], require, moment, judge_document)
            elif kind == "hearing.start":
                c = entity(result["cases"], p["case_id"])
                require(c["status"] == "pending", "case is closed")
                if c["court_id"] == "CA9":
                    life.phase(c, "merits", require=require)
                    require(c["panel_kind"] != "quorum", "quorum continues submitted case")
                fresh(c["hearings"], p["hearing_id"])
                if c["court_id"] == "CA9" and p["kind"] == "consideration_on_briefs":
                    ca9.no_argument(c, p, require)
                c["hearings"][p["hearing_id"]] = {"id": p["hearing_id"], "kind": p["kind"],
                    "status": "in_progress", "started_at": campaign["game_time"], "ended_at": None}
                if c["court_id"] == "CA9":
                    c["hearings"][p["hearing_id"]]["panel_epoch"] = c["panel_epoch"]
                if c["court_id"] == "CA9" and p["kind"] == "consideration_on_briefs":
                    c["hearings"][p["hearing_id"]].update(no_argument_votes=deepcopy(p["no_argument_votes"]), no_argument_reason=p["no_argument_reason"], briefs_and_record_reviewed=True)
            elif kind == "hearing.complete":
                c = entity(result["cases"], p["case_id"])
                h = entity(c["hearings"], p["hearing_id"])
                require(h["status"] == "in_progress", "hearing is not in progress")
                if c["court_id"] == "CA9":
                    life.phase(c, "merits", require=require)
                    require(h.get("panel_epoch") == c["panel_epoch"], "old panel hearing")
                h.update(status="completed", ended_at=campaign["game_time"])
                # Deliberation, record closing and drafting are deliberately independent.
            elif kind == "task.assign":
                fresh(result["tasks"], p["task_id"])
                entity(result["cases"], p["case_id"])
                person = entity(result["people"], p["assignee_id"])
                require(person.get("active") is True, "assignee is inactive")
                if campaign.get("organization"):
                    org.task_guard(result,p,require)
                require(moment(p["due_at"]) >= moment(campaign["game_time"]), "task due date is in the past")
                result["tasks"][p["task_id"]] = {"id": p["task_id"], "case_id": p["case_id"],
                    "assignee_id": p["assignee_id"], "instructions": p["instructions"],
                    "due_at": p["due_at"], "status": "assigned", "output_document_id": None}
                if campaign.get("organization"):
                    result["tasks"][p["task_id"]].update(assigning_judge_id=p["assigning_judge_id"],task_kind=p["task_kind"])
            elif kind == "task.complete":
                task = entity(result["tasks"], p["task_id"])
                require(task["status"] == "assigned", "task is not pending")
                doc = judge_document(result, p["output_document_id"])
                require(doc["case_id"] == task["case_id"], "task output belongs to another case")
                if campaign.get("organization"):
                    require(doc["status"]=="internal" or task["task_kind"]=="administration","substantive clerk work must remain internal")
                task.update(status="completed", output_document_id=p["output_document_id"])
            elif kind == "conference.record":
                c = entity(result["cases"], p["case_id"])
                require(c["court_id"] == "CA9" and c["status"] == "pending", "conference rule only for CA9 pending case")
                require(c["writing_status"] == "not_started", "initial conference already passed; use opinion positions for revisions")
                life.phase(c, "merits", require=require)
                if campaign.get("organization"):
                    org.conference_guard(result,c,require)
                conf = ca9.conference(c,p,require)
                conf["panel_epoch"] = c["panel_epoch"]
                if c["panel_kind"] == "limited_en_banc":
                    coalition = [j for j,v in conf["votes"].items() if v == conf["majority_disposition"]]
                    require(all(type(result["people"][j].get("seniority_rank")) is int for j in coalition), "en banc seniority missing")
                    require(p.get("assigning_judge_id") == min(coalition,key=lambda j:result["people"][j]["seniority_rank"]), "GO 5.7 senior majority judge assigns")
                c.setdefault("conferences", []).append(conf)
            elif kind == "draft.start":
                c = entity(result["cases"], p["case_id"])
                require(c["status"] == "pending" and c["writing_status"] == "not_started", "cannot start draft")
                require(p["author_id"] in c["assigned_judges"], "author is outside panel")
                if c["court_id"] == "CA9":
                    life.phase(c, "merits", require=require)
                    require(c.get("conferences") and c["conferences"][-1]["author_id"] == p["author_id"] and c["conferences"][-1]["panel_epoch"] == c["panel_epoch"], "CA9 current conference author required")
                c["writing_status"] = "drafting"
            elif kind == "opinion.circulate":
                obj = deepcopy(p["opinion"])
                fresh(result["opinions"], obj["id"])
                c = entity(result["cases"], obj["case_id"])
                require(c["writing_status"] in {"drafting", "circulating"}, "draft not started")
                if obj.get("supersedes"):
                    old = entity(result["opinions"], obj["supersedes"])
                    require(old["case_id"] == obj["case_id"], "revision crosses cases")
                if c["court_id"] == "CA9":
                    life.phase(c, "merits", require=require)
                    obj.update(panel_epoch=c["panel_epoch"], panel_judges=list(c["assigned_judges"]))
                    if obj.get("supersedes"):
                        require(old["status"]=="circulating" and old.get("panel_epoch")==c["panel_epoch"] and old["author_id"]==obj["author_id"],"invalid current draft revision")
                        old["status"]="superseded"
                obj.update(positions={}, status="circulating")
                result["opinions"][obj["id"]] = obj
                c["writing_status"] = "circulating"
            elif kind == "opinion.position":
                opinion = entity(result["opinions"], p["opinion_id"])
                require(opinion["status"] == "circulating", "opinion is not circulating")
                c = entity(result["cases"], opinion["case_id"])
                if c["court_id"] == "CA9":
                    life.phase(c, "merits", require=require)
                    require(opinion.get("panel_epoch")==c["panel_epoch"],"old panel draft")
                opinion["positions"][p["judge_id"]] = {"disposition": p["disposition"],
                    "stance": p["stance"], "joined_parts": p["joined_parts"], "comment": p.get("comment", "")}
            elif kind == "opinion.issue":
                opinion = entity(result["opinions"], p["opinion_id"])
                c = entity(result["cases"], opinion["case_id"])
                require(opinion["status"] == "circulating", "opinion already issued")
                require(set(opinion["positions"]) == set(c["assigned_judges"]), "panel positions incomplete")
                require(p.get("rule_basis") and p.get("legal_review_completed") is True,
                        "issuance requires court-specific legal review")
                require(p["opinion_kind"] in {"majority", "plurality", "concurrence", "dissent", "order"},
                        "invalid opinion kind")
                if c["court_id"] == "CA9":
                    life.phase(c, "merits", require=require)
                    require(opinion.get("panel_epoch")==c["panel_epoch"],"old panel draft")
                    if p["opinion_kind"] in {"majority","plurality","order"}:
                        require(not any(o["id"]!=opinion["id"] and o["case_id"]==c["id"] and o.get("panel_epoch")==c["panel_epoch"] and o["status"]=="issued" and o.get("opinion_kind") in {"majority","plurality","order"} for o in result["opinions"].values()),"controlling disposition already issued")
                    opinion.update(ca9.issuance(c, opinion, p, require))
                opinion.update(status="issued", issued_at=campaign["game_time"],
                    opinion_kind=p["opinion_kind"], rule_basis=p["rule_basis"])
            elif kind == "precedent.register":
                obj = deepcopy(p["precedent"])
                fresh(result["precedents"], obj["id"])
                require(obj.get("source_type") == "issued_simulated_opinion" and obj.get("issued_at"),
                        "drafts cannot be registered as precedent")
                opinion = entity(result["opinions"], obj["opinion_id"])
                require(opinion["status"] == "issued", "opinion has not been issued")
                require(obj["authority_status"] in {"binding", "persuasive", "nonprecedential", "undetermined"}
                        and obj.get("scope") and obj.get("rule_basis"), "precedent needs scope and rule basis")
                if result["cases"][opinion["case_id"]]["court_id"] == "CA9" and obj["authority_status"] == "binding":
                    require(opinion.get("publication_form") == "OPINION" and opinion["opinion_kind"] == "majority", "CA9 binding precedent requires published majority opinion")
                moment(obj["issued_at"])
                result["precedents"][obj["id"]] = obj
            elif kind == "deadline.add":
                obj = deepcopy(p["deadline"])
                fresh(result["deadlines"], obj["id"])
                obj["status"] = "pending"
                result["deadlines"][obj["id"]] = obj
            elif kind == "deadline.satisfy":
                d = entity(result["deadlines"], p["deadline_id"])
                doc = judge_document(result, p["document_id"])
                require(doc["case_id"] == d["case_id"], "deadline document belongs to another case")
                d.update(status="satisfied", document_id=p["document_id"])
            elif kind == "time.advance":
                require(p.get("user_authorized") is True, "time progression requires user authorization")
                require(type(p["minutes"]) is int and 0 < p["minutes"] <= 525600, "invalid time increment")
                now = moment(campaign["game_time"]) + timedelta(minutes=p["minutes"])
                campaign["game_time"] = now.isoformat()
                for d in result["deadlines"].values():
                    if d["status"] == "pending" and moment(d["due_at"]) < now:
                        d["status"] = "overdue"
                # No automatic evidence, memoranda, judgments or career promotion.
            elif kind == "scene.set":
                require(isinstance(p["scene"], str) and p["scene"], "empty scene")
                campaign["scene"] = p["scene"]
            elif kind == "career.record":
                require(p.get("basis") and p.get("effective_at"), "career event needs basis and effective date")
                moment(p["effective_at"])
                result["career"].append(deepcopy(p))
            else:
                raise Invalid(f"unsupported event: {kind}")
        result["applied_events"][event["id"]] = signature
        result["revision"] += 1
        validate_state(result, profiles, allow_training)
    return result
