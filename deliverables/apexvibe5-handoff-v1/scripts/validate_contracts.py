"""Validate the handoff package only. This is not a backend/browser E2E test."""
from pathlib import Path
from hashlib import sha256
from decimal import Decimal
from datetime import datetime, timezone
from copy import deepcopy
import importlib.metadata
import json
import sqlite3
import tempfile
import re
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource
from openapi_spec_validator import validate as validate_openapi
from reference_demo import analyze_module, calculate_case, apply_adjustment
from build_reference_db import build

ROOT=Path(__file__).resolve().parents[1]
CHECKS=[]

def load(path): return json.loads((ROOT/path).read_text())
def check(label, condition):
    if not condition:
        raise AssertionError(label)
    CHECKS.append(label)

def main():
    schema_dir=ROOT/'contracts/schemas'
    schema_files=sorted(schema_dir.glob('*.json'))
    resources={p.as_uri():Resource.from_contents(json.loads(p.read_text())) for p in schema_files}
    registry=Registry().with_resources(resources.items())
    for p in schema_files:
        Draft202012Validator.check_schema(json.loads(p.read_text()))
    check('All JSON Schema definitions are valid Draft 2020-12',bool(schema_files))
    index=load('validation/example-index.json')
    for entry in index:
        uri=(schema_dir/f'{entry["schema"]}.schema.json').as_uri()
        validator=Draft202012Validator({'$ref':uri},registry=registry,format_checker=FormatChecker())
        validator.validate(load(entry['path']))
    check('All indexed JSON examples satisfy their exact schema',len(index)>=50)
    api=load('contracts/openapi.json')
    validate_openapi(api)
    check('OpenAPI 3.1 document is valid',True)
    components=api['components']['schemas']
    check('OpenAPI and standalone schemas have identical models',set(components)==set(load('contracts/schemas/common.schema.json')['$defs']))
    op_ids=[op['operationId'] for v in api['paths'].values() for op in v.values()]
    check('API operation IDs are unique',len(op_ids)==len(set(op_ids)))
    # All local references and markdown links resolve inside this package.
    for p in ROOT.rglob('*.json'):
        json.loads(p.read_text())
    for p in ROOT.rglob('*.md'):
        for target in re.findall(r'\]\(([^)]+)\)',p.read_text()):
            if '://' not in target and not target.startswith('#'):
                check(f'Local document link resolves: {p.name} -> {target}',(p.parent/target.split('#')[0]).exists())
    policy=load('contracts/risk-policy.json')
    caps=policy['module_caps']
    check('Module caps sum to 100',sum(caps.values())==100)
    check('Only two risk bands',components['RiskBand']['enum']==['LOW','HIGH'])
    check('Threshold boundary 29 LOW / 30 HIGH',29<policy['high_min_inclusive']<=30)
    check('Negative adjustment clips locally and effective delta remains additive',apply_adjustment(5,-10,15)==(0,-5))
    check('Positive adjustment clips locally and effective delta remains additive',apply_adjustment(12,10,15)==(15,3))
    rejected=False
    try: apply_adjustment(5,-16,15)
    except ValueError: rejected=True
    check('Out-of-bounds adjustment is rejected',rejected)
    pdf=load('fixtures/pdf-acroform-review.json')
    for case in ['case_1','case_2']:
        inv=load(f'examples/{case}/invoice.json')
        raw=load(f'fixtures/{case}-raw-field-map.json')['fields']
        check(f'{case}: PDF and spreadsheet invoice number agree',pdf[case]['fields']['invoice no']==raw['invoice_number']==inv['invoice_number'])
        check(f'{case}: PDF, spreadsheet and JSON quantity agree',int(pdf[case]['fields']['no of units 1'])==raw['quantity']==inv['line_items'][0]['quantity'])
        check(f'{case}: PDF, spreadsheet and JSON unit price agree',Decimal(pdf[case]['fields']['unit value 1'])==Decimal(str(raw['unit_price']))==Decimal(inv['line_items'][0]['unit_price']))
        check(f'{case}: PDF, spreadsheet and JSON amount agree',Decimal(pdf[case]['fields']['invoice total'])==Decimal(str(raw['invoice_total']))==Decimal(inv['total']))
        check(f'{case}: template checkbox values match reviewed mapping',pdf[case]['fields']['Check Box3']=='/no' and inv['consignee_same_as_buyer'] is True and pdf[case]['fields']['Radio Button1']=='/no' and inv['declared_related'] is False)
        ws=load(f'examples/{case}/workspace.json')
        check(f'{case}: seven isolated modules',{m['module_key'] for m in ws['modules']}==set(caps) and all(m['case_id']==case for m in ws['modules']))
        for key in caps:
            inp=load(f'examples/{case}/modules/{key}.input.json')
            out=load(f'examples/{case}/modules/{key}.output.json')
            computed=analyze_module(inp,policy)
            for field in ['state','ai_score','matched_rule_ids','missing_inputs','blocking_flags']:
                check(f'{case}/{key}: calculated {field} agrees with example',out[field]==computed[field])
            canonical=json.dumps(inp,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
            check(f'{case}/{key}: input hash bound to content',sha256(canonical).hexdigest()==out['provenance']['input_hash'])
            allowed_sources={x['source_id'] for x in inp['evidence']}|{x['supplement_id'] for x in inp['supplements']}
            check(f'{case}/{key}: findings reference only supplied sources',all(s['source_id'] in allowed_sources for f in out['findings'] for s in f['source_refs']))
        result=calculate_case(case)
        snapshot=ws['aggregate']['current_result']
        check(f'{case}: reference computation equals snapshot',result['score']==snapshot['final_risk_score'] and result['risk_band']==snapshot['risk_band'])
        check(f'{case}: financing amount agrees',result['advance_amount']==ws['aggregate']['decision']['advance_amount'])
    for entry in index:
        if entry['schema']!='Workspace': continue
        ws=load(entry['path']); ag=ws['aggregate']; snapshot=ag['current_result']
        if snapshot is not None:
            check(f'{entry["path"]}: total equals sum of final module scores',snapshot['final_risk_score']==sum(m['final_score'] for m in ws['modules']))
            check(f'{entry["path"]}: AI plus effective adjustments adds up',snapshot['ai_total']+snapshot['effective_adjustment_total']==snapshot['final_risk_score'])
            check(f'{entry["path"]}: current outputs use current inputs',all(m['freshness']=='current' and m['input_version']==m['evaluated_input_version'] for m in ws['modules']))
        else:
            check(f'{entry["path"]}: invalid aggregate has no financing recommendation',ag['decision']['status']=='pending' and ag['decision']['advance_amount'] is None)
    base=load('examples/case_2/modules/relationship.input.json')
    for amount,rule in [('15999.99','TRADE_SCALE_NORMAL'),('16000.00','TRADE_SCALE_ELEVATED'),('39999.99','TRADE_SCALE_ELEVATED'),('40000.00','TRADE_SCALE_HIGH')]:
        variant=deepcopy(base);variant['facts']['amount']=amount
        check(f'Trade-size boundary {amount}',analyze_module(variant,policy)['matched_rule_ids']==[rule])
    original=analyze_module(base,policy)
    variant=deepcopy(base);variant['case_id']='arbitrary_filename_case_low'
    check('Changing a case label does not change score',analyze_module(variant,policy)==original)
    variant=deepcopy(base);variant['reference_records']=[]
    check('Missing baseline is not zero risk',analyze_module(variant,policy)['ai_score'] is None)
    payment=load('examples/case_1/modules/payment_history.input.json')
    payment['reference_records'][0]['data']['records'][0]['defaulted']=True
    check('New substantive default evidence increases module risk',analyze_module(payment,policy)['ai_score']==15)
    payment=load('examples/case_1/modules/payment_history.input.json')
    for row in payment['reference_records'][0]['data']['records']: row['late_days']=0
    check('Changed payment facts can reduce module risk',analyze_module(payment,policy)['ai_score']==0)
    for f in load('fixtures/source-manifest.json')['files']:
        data=(ROOT/'source'/f['filename']).read_bytes()
        check(f'Original attachment hash preserved: {f["filename"]}',sha256(data).hexdigest()==f['sha256'] and len(data)==f['bytes'])
    db=sqlite3.connect(f'file:{ROOT / "db/reference.sqlite3"}?mode=ro',uri=True)
    check('Reference database integrity',db.execute('PRAGMA integrity_check').fetchone()[0]=='ok')
    check('Reference database foreign keys',not db.execute('PRAGMA foreign_key_check').fetchall())
    check('Reference database has no fabricated assessed cases',db.execute('SELECT COUNT(*) FROM cases').fetchone()[0]==0)
    check('Reference database has two shared entities',db.execute('SELECT COUNT(*) FROM entity_profiles').fetchone()[0]==2)
    check('Reference database has six synthetic source records',db.execute('SELECT COUNT(*) FROM reference_records WHERE synthetic=1').fetchone()[0]==6)
    expected=load('fixtures/local-reference-data.json')['records']
    for row in expected:
        value=db.execute('SELECT data_json FROM reference_records WHERE source_id=?',(row['source_id'],)).fetchone()[0]
        check(f'Database matches JSON: {row["source_id"]}',json.loads(value)==row['data'])
    db.close()
    with tempfile.TemporaryDirectory() as td:
        path=Path(td)/'rebuild.sqlite3'
        build(path)
        rebuilt=sqlite3.connect(path)
        check('Reference DB can be rebuilt from delivered scripts',rebuilt.execute('SELECT COUNT(*) FROM reference_records').fetchone()[0]==6)
        rebuilt.close()
        from_seed=sqlite3.connect(':memory:')
        from_seed.executescript((ROOT/'db/schema.sql').read_text())
        from_seed.executescript((ROOT/'db/seed.sql').read_text())
        check('SQL DDL and seed execute independently',from_seed.execute('SELECT COUNT(*) FROM reference_records').fetchone()[0]==6)
        from_seed.close()
    report={'status':'passed','scope':'static_contract_and_reference_calculation_only_not_backend_e2e','validated_at':datetime.now(timezone.utc).isoformat(),'counts':{'schemas':len(schema_files),'json_examples':len(index),'module_definitions':len(caps),'api_operations':len(op_ids),'checks':len(CHECKS)},'tools':{p:importlib.metadata.version(p) for p in ['jsonschema','openapi-spec-validator']},'demo_results':{c:calculate_case(c) for c in ['case_1','case_2']},'checks':CHECKS,'not_verified':['FastAPI HTTP runtime','Worker lease recovery runtime','actual LLM execution','Next.js browser navigation','GitHub deployment']}
    (ROOT/'validation/report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k in ['status','scope','counts','demo_results']},ensure_ascii=False,indent=2))

if __name__=='__main__': main()
