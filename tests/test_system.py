from copy import deepcopy
from pathlib import Path
import shutil
import tempfile
import unittest
from judgesim.engine import Invalid, apply_batch, initial_state, reference, view
from judgesim.storage import read_json, write_json, verify, write_checkpoint, check_documents, safe, sha
from scripts.process_requests import process

ROOT = Path(__file__).resolve().parents[1]
PROFILES = {'TRAINING-APPEAL': {'id':'TRAINING-APPEAL', 'status':'training_only',
    'matter_types':['training_civil'], 'hearing_kinds':['oral_argument']}}

def ev(i, event_type, **payload):
    return {'id':i, 'type':event_type, 'payload':payload}

def document(key):
    return deepcopy(read_json(ROOT/'examples/documents.json')[key])

def fixture():
    return apply_batch(initial_state(), read_json(ROOT/'examples/scenario.json')['events'],
                       PROFILES, allow_training=True)

def run(state, events):
    return apply_batch(state, events, PROFILES, allow_training=True)

def draft(state):
    return run(state, [ev('DRAFT','draft.start',case_id='C-001',author_id='P-JUDGE'),
        ev('DOC5','document.register',document=document('D-005')),
        ev('CIRC','opinion.circulate',opinion={'id':'O-1','case_id':'C-001','document_id':'D-005',
            'author_id':'P-JUDGE','parts':['I','II']})])

class EventTests(unittest.TestCase):
    def test_live_campaign_unconfigured(self):
        s=verify(ROOT)
        self.assertEqual(s['campaign']['status'],'setup_required')
        self.assertIsNone(s['campaign']['player']); self.assertFalse(s['cases'])

    def test_training_not_playable_as_real_court(self):
        with self.assertRaises(Invalid):
            apply_batch(initial_state(),read_json(ROOT/'examples/scenario.json')['events'],PROFILES)

    def test_unresearched_court_rejected(self):
        p=deepcopy(PROFILES); p['TRAINING-APPEAL']['status']='research_required'
        with self.assertRaises(Invalid):
            apply_batch(initial_state(),read_json(ROOT/'examples/scenario.json')['events'],p)

    def test_hearing_end_not_drafting_or_final_judgment(self):
        s=fixture(); out=run(s,[ev('H1','hearing.start',case_id='C-001',hearing_id='OA',kind='oral_argument'),
                               ev('H2','hearing.complete',case_id='C-001',hearing_id='OA')])
        self.assertEqual(out['cases']['C-001']['hearings']['OA']['status'],'completed')
        self.assertEqual(out['cases']['C-001']['writing_status'],'not_started')
        self.assertEqual(out['cases']['C-001']['status'],'pending')
        self.assertEqual(out['campaign']['game_time'],s['campaign']['game_time'])

    def test_failed_batch_atomic(self):
        s=fixture(); old=deepcopy(s)
        with self.assertRaises(Invalid):
            run(s,[ev('H1','hearing.start',case_id='C-001',hearing_id='OA',kind='oral_argument'),
                   ev('H2','hearing.complete',case_id='C-001',hearing_id='MISSING')])
        self.assertEqual(s,old)

    def test_idempotency_and_id_collision(self):
        e=ev('SC','scene.set',scene='conference'); s=run(fixture(),[e])
        self.assertEqual(run(s,[e]),s)
        e['payload']['scene']='courtroom'
        with self.assertRaises(Invalid): run(s,[e])

    def test_wrong_court_and_capability(self):
        s=fixture()
        with self.assertRaises(Invalid):
            run(s,[ev('BAD','hearing.start',case_id='C-001',hearing_id='TRIAL',kind='jury_trial')])
        c=deepcopy(s['cases']['C-001']); c.update(id='C-OTHER',court_id='OTHER')
        with self.assertRaises(Invalid): run(s,[ev('BAD2','case.register',case=c)])

    def test_world_evidence_filtered_and_not_citable(self):
        s=fixture(); self.assertIn('D-003',s['documents'])
        self.assertNotIn('D-003',view(s)['documents'])
        with self.assertRaises(Invalid): reference(s,{'document_id':'D-003','page':1})

    def test_nonexistent_page_rejected(self):
        s=fixture(); self.assertEqual(reference(s,{'document_id':'D-001','page':1})['id'],'D-001')
        for page in [0,2,True]:
            with self.assertRaises(Invalid): reference(s,{'document_id':'D-001','page':page})

    def test_unfiled_cannot_become_judge_record(self):
        d=document('D-003'); d.update(id='LEAK',access='judge')
        with self.assertRaises(Invalid): run(fixture(),[ev('LEAK','document.register',document=d)])

    def test_task_needs_actual_output(self):
        s=run(fixture(),[ev('TASK','task.assign',task_id='T1',case_id='C-001',assignee_id='P-CLERK',
            instructions='Prepare record inventory.',due_at='2026-01-05T17:00:00-05:00')])
        with self.assertRaises(Invalid):
            run(s,[ev('DONE','task.complete',task_id='T1',output_document_id='MISSING')])
        out=run(s,[ev('DOC4','document.register',document=document('D-004')),
                   ev('DONE','task.complete',task_id='T1',output_document_id='D-004')])
        self.assertEqual(out['tasks']['T1']['status'],'completed')

    def test_time_requires_authorization_and_no_automatic_memo(self):
        s=run(fixture(),[ev('DL','deadline.add',deadline={'id':'DL1','case_id':'C-001',
            'due_at':'2026-01-05T09:30:00-05:00','basis':'Fictional training scheduling direction'})])
        with self.assertRaises(Invalid): run(s,[ev('TIME','time.advance',minutes=60,user_authorized=False)])
        out=run(s,[ev('TIME','time.advance',minutes=60,user_authorized=True)])
        self.assertEqual(out['deadlines']['DL1']['status'],'overdue')
        self.assertFalse(out['tasks']); self.assertEqual(out['career'],[])

    def test_partial_joins_revision_not_copied(self):
        s=run(draft(fixture()),[ev('POS','opinion.position',opinion_id='O-1',judge_id='P-JUDGE2',
            disposition='affirm',stance='concur',joined_parts=['I'])])
        self.assertEqual(s['opinions']['O-1']['positions']['P-JUDGE2']['joined_parts'],['I'])
        out=run(s,[ev('DOC6','document.register',document=document('D-006')),
            ev('CIRC2','opinion.circulate',opinion={'id':'O-2','case_id':'C-001','document_id':'D-006',
                'author_id':'P-JUDGE','parts':['I','II'],'supersedes':'O-1'})])
        self.assertEqual(out['opinions']['O-2']['positions'],{})
        self.assertEqual(out['opinions']['O-1'],s['opinions']['O-1'])
        with self.assertRaises(Invalid):
            run(out,[ev('BADPOS','opinion.position',opinion_id='O-2',judge_id='P-CLERK',
                disposition='affirm',stance='join',joined_parts=['I'])])

    def test_draft_not_precedent(self):
        with self.assertRaises(Invalid):
            run(draft(fixture()),[ev('PREC','precedent.register',precedent={'id':'PR1','opinion_id':'O-1',
                'origin':'simulation','source_type':'issued_simulated_opinion',
                'issued_at':'2026-01-05T09:00:00-05:00','authority_status':'undetermined',
                'scope':'training','rule_basis':'training only'})])

class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.root=Path(self.temp.name)
        shutil.copytree(ROOT,self.root,dirs_exist_ok=True,ignore=shutil.ignore_patterns('.git','__pycache__'))
    def tearDown(self): self.temp.cleanup()

    def test_publish_and_new_session_restore(self):
        result=process(self.root)
        # Already-published health request in deployed repositories is also valid.
        self.assertIn(result, [[],[{'request_id':'REQ-0001-connection','status':'accepted'}]])
        s=verify(self.root); self.assertEqual(s['revision'],1)
        self.assertEqual(s['campaign']['status'],'setup_required')
        self.assertEqual(read_json(self.root/'CURRENT.json')['checkpoint'],'S0001-connection-check')
        self.assertEqual(process(self.root),[])

    def test_stale_request_does_not_change_current(self):
        process(self.root); old=read_json(self.root/'CURRENT.json')
        p=read_json(self.root/'requests/REQ-0001-connection.json')
        p.update(request_id='REQ-0002-stale',checkpoint='S0002-stale')
        write_json(self.root/'requests/REQ-0002-stale.json',p); process(self.root)
        self.assertEqual(read_json(self.root/'receipts/REQ-0002-stale.json')['status'],'rejected')
        self.assertEqual(read_json(self.root/'CURRENT.json'),old)

    def test_processed_request_immutable(self):
        process(self.root); p=read_json(self.root/'requests/REQ-0001-connection.json')
        p['checkpoint']='REWRITE'; write_json(self.root/'requests/REQ-0001-connection.json',p)
        with self.assertRaises(Invalid): process(self.root)

    def test_snapshot_tamper(self):
        p=self.root/'saves/S0000-setup/state.json'; s=read_json(p)
        s['campaign']['scene']='tampered'; write_json(p,s)
        with self.assertRaises(Invalid): verify(self.root)

    def training_save(self):
        # Point to genesis for isolated fixture even after the deployed smoke save.
        write_json(self.root/'courts/profiles.json',{'schema_version':1,'profiles':PROFILES})
        s=fixture(); write_checkpoint(self.root,'TRAINING',s,read_json(ROOT/'examples/scenario.json')['events'],
            parent='S0000-setup',parent_state=initial_state())
        return s

    def test_original_fixed_and_replay_restores(self):
        s=self.training_save(); self.assertEqual(verify(self.root,allow_training=True),s)
        p=self.root/document('D-001')['path']; p.write_text(p.read_text()+'Changed\n')
        with self.assertRaises(Invalid): verify(self.root,allow_training=True)

    def test_page_layout_checked_beyond_hash(self):
        s=self.training_save(); p=self.root/document('D-001')['path']
        p.write_text('<!-- PAGE 2 -->\nBroken\n'); s['documents']['D-001']['sha256']=sha(p)
        with self.assertRaises(Invalid): check_documents(self.root,s)

    def test_initial_record_cannot_be_incomplete(self):
        s=fixture(); s['cases']['C-001']['initial_document_ids'].append('MISSING')
        with self.assertRaises(Invalid): check_documents(self.root,s)

    def test_document_citation_target_is_checked(self):
        s=fixture()
        s['documents']['D-002']['citations']=[{'document_id':'D-001','page':99}]
        with self.assertRaises(Invalid): check_documents(self.root,s)

    def test_source_overview_cannot_be_promoted_to_ready_court(self):
        p=deepcopy(PROFILES['TRAINING-APPEAL'])
        p.update(status='ready', source_ids=['SRC-US-STRUCTURE'], checked_on='2026-10-24',
                 role='test', jurisdiction='test', appeal_route='test', appointment='test',
                 staffing='test', rules='test')
        write_json(self.root/'courts/profiles.json',{'schema_version':1,'profiles':{p['id']:p}})
        with self.assertRaises(Invalid): verify(self.root)

    def test_paths_cannot_escape(self):
        with self.assertRaises(Invalid): safe(self.root,'../outside')

    def test_smoke_does_not_play_a_case(self):
        process(self.root); s=verify(self.root)
        self.assertFalse(s['cases']); self.assertIsNone(s['campaign']['game_time'])

if __name__ == '__main__': unittest.main()
