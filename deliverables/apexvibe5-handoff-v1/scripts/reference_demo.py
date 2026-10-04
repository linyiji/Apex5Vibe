"""Deterministic reference calculations, not an AI service or an API backend.

Consumes module facts and synthetic local references. Does not read expected scores
or choose a score from case names, filenames, or a scenario label.
"""
from pathlib import Path
from decimal import Decimal, ROUND_HALF_UP
from statistics import median
import json

ROOT = Path(__file__).resolve().parents[1]

def load(path):
    return json.loads((ROOT / path).read_text())

def analyze_module(inp, policy):
    key=inp['module_key']
    facts=inp['facts']
    refs={r['kind']:r['data'] for r in inp['reference_records']}
    required=load(f'contracts/modules/{key}.json')['required_reference_kinds']
    missing=[k for k in required if k not in refs]
    if missing:
        return {'state':'needs_info','ai_score':None,'matched_rule_ids':[],'missing_inputs':missing,'blocking_flags':[]}
    blocks=[]
    if key=='invoice_integrity':
        from datetime import date, timedelta
        inv=facts['invoice']
        correct=all(Decimal(str(x['quantity']))*Decimal(x['unit_price'])==Decimal(x['line_total']) for x in inv['line_items'])
        correct &= sum(Decimal(x['line_total']) for x in inv['line_items'])==Decimal(inv['subtotal'])
        correct &= Decimal(inv['subtotal'])+sum(Decimal(x) for x in inv['charges'].values())==Decimal(inv['total'])
        correct &= date.fromisoformat(inv['invoice_date'])+timedelta(days=inv['payment_term_days'])==date.fromisoformat(inv['due_date'])
        rule='INTEGRITY_OK' if correct else 'INTEGRITY_CONFLICT'
        if not correct: blocks=['invoice_integrity_conflict']
    elif key in ('buyer_verification','seller_verification'):
        p=refs['entity_profile']
        current=facts['entity']
        match=all(current[k].strip().casefold()==p[k].strip().casefold() for k in ['legal_name','tax_id','country','address'])
        rule=('BUYER' if key=='buyer_verification' else 'SELLER')+('_MATCH' if match else '_CONFLICT')
        if not match: blocks=['entity_mismatch']
    elif key=='relationship':
        history=refs['trade_history']
        comparable=[Decimal(t['amount']) for t in history['trades'] if t['seller_id']==facts['seller_id'] and t['buyer_id']==facts['buyer_id'] and t['sku']==facts['sku'] and t['currency']==facts['currency'] and t['status']=='completed' and history['window_start']<=t['invoice_date']<=history['window_end'] and t['invoice_date']<facts['invoice_date']]
        if not comparable or median(comparable)<=0:
            return {'state':'needs_info','ai_score':None,'matched_rule_ids':[],'missing_inputs':['comparable_trade_baseline'],'blocking_flags':[]}
        ratio=Decimal(facts['amount'])/median(comparable)
        if facts['declared_related'] != history['declared_related']:
            rule='RELATED_PARTY_CONFLICT'
        else:
            rule='TRADE_SCALE_NORMAL' if ratio<2 else 'TRADE_SCALE_ELEVATED' if ratio<5 else 'TRADE_SCALE_HIGH'
    elif key=='market_price':
        b=refs['market_benchmark']
        deviation=Decimal(0)
        for item in facts['line_items']:
            if not (item['sku']==b['sku'] and item['unit']==b['unit'] and facts['currency']==b['currency'] and facts['trade_terms']==b['trade_terms'] and facts['delivery_location']==b['delivery_location']):
                return {'state':'needs_info','ai_score':None,'matched_rule_ids':[],'missing_inputs':['comparable_market_benchmark'],'blocking_flags':[]}
            price,low,high=map(Decimal,[item['unit_price'],b['lower'],b['upper']])
            deviation=max(deviation,(low-price)/low if price<low else (price-high)/high if price>high else Decimal(0))
        rule='PRICE_IN_RANGE' if deviation==0 else 'PRICE_DEVIATION_MINOR' if deviation<=Decimal('0.25') else 'PRICE_DEVIATION_HIGH'
    elif key=='payment_history':
        records=[r for r in refs['payment_history']['records'] if r['buyer_id']==facts['buyer_id'] and r['due_date']<=inp['as_of'] and r['paid_date']<=inp['as_of']]
        if not records:
            return {'state':'needs_info','ai_score':None,'matched_rule_ids':[],'missing_inputs':['matured_payment_records'],'blocking_flags':[]}
        ratio=Decimal(sum(r['late_days']>0 for r in records))/Decimal(len(records))
        defaults=any(r['defaulted'] for r in records)
        rule='PAYMENT_HIGH' if defaults or ratio>Decimal('0.5') else 'PAYMENT_DELAY' if ratio>Decimal('0.2') else 'PAYMENT_MINOR_DELAY' if ratio>0 else 'PAYMENT_ON_TIME'
    elif key=='duplicate_financing':
        registry=refs['financing_registry']
        if not registry['coverage_complete_for_demo']:
            return {'state':'needs_info','ai_score':None,'matched_rule_ids':[],'missing_inputs':['financing_registry_coverage'],'blocking_flags':[]}
        match=any(r.get('status')=='active' and all(r.get(k)==v for k,v in facts.items()) for r in registry['records'])
        rule='ACTIVE_FINANCING_MATCH' if match else 'NO_LOCAL_FINANCING_MATCH'
        if match: blocks=['confirmed_duplicate_financing']
    else:
        raise ValueError(f'Unknown module {key}')
    score=next(r['points'] for r in policy['rules'][key] if r['rule_id']==rule)
    return {'state':'succeeded','ai_score':score,'matched_rule_ids':[rule],'missing_inputs':[],'blocking_flags':blocks}

def apply_adjustment(ai_score, requested, cap):
    if not isinstance(requested,int) or isinstance(requested,bool) or not -cap<=requested<=cap:
        raise ValueError('adjustment outside module bounds')
    final=max(0,min(cap,ai_score+requested))
    return final,final-ai_score

def calculate_case(case_dir):
    policy=load('contracts/risk-policy.json')
    scores={}
    for key in policy['module_caps']:
        inp=load(f'examples/{case_dir}/modules/{key}.input.json')
        scores[key]=analyze_module(inp,policy)
    if any(x['ai_score'] is None for x in scores.values()):
        return {'status':'incomplete','risk_band':None,'score':None}
    total=sum(x['ai_score'] for x in scores.values())
    high=total>=policy['high_min_inclusive']
    blocked=any(x['blocking_flags'] for x in scores.values())
    invoice=load(f'examples/{case_dir}/invoice.json')
    advance=None if high or blocked else str((Decimal(invoice['total'])*Decimal(policy['advance_rate'])).quantize(Decimal('0.01'),rounding=ROUND_HALF_UP))
    return {'score':total,'risk_band':'HIGH' if high else 'LOW','decision':'manual_review' if high or blocked else 'eligible','advance_amount':advance,'currency':invoice['currency'],'module_scores':{k:v['ai_score'] for k,v in scores.items()},'engine':'deterministic_reference_not_live_ai'}

if __name__=='__main__':
    print(json.dumps({case:calculate_case(case) for case in ['case_1','case_2']},ensure_ascii=False,indent=2))
