"""AI composes an explanation from verified clauses; it cannot invent claims."""
import json
import os
import httpx

def explain(result):
    fallback={'source':'rules','note':'Complete evidence-based explanation. AI is not enabled.','order':[f['id'] for f in result['findings']]}
    if os.getenv('PLUQ_AI_ENABLED')!='true': return fallback
    key,model=os.getenv('OPENAI_API_KEY'),os.getenv('OPENAI_MODEL')
    if not key or not model or not result['findings']:
        return {**fallback,'note':'Rule-based explanation: AI is unavailable or there are no findings to explain.'}
    ids=fallback['order']
    schema={'type':'object','properties':{'order':{'type':'array','items':{'type':'string','enum':ids}},'intro':{'type':'string','enum':['verify_sender','official_channel']}},'required':['order','intro'],'additionalProperties':False}
    try:
        with httpx.Client(timeout=12,follow_redirects=False) as client:
            response=client.post('https://api.openai.com/v1/responses',headers={'Authorization':f'Bearer {key}'},json={
                'model':model,'store':False,'max_output_tokens':600,
                'instructions':'Compose an explanation plan for an ordinary person from these verified findings. Order by usefulness and choose an introduction. Include each ID exactly once. Never infer new evidence.',
                'input':json.dumps([{'id':f['id'],'detected':f['detected'],'why':f['why']} for f in result['findings']]),
                'text':{'format':{'type':'json_schema','name':'explanation','strict':True,'schema':schema}}})
            response.raise_for_status()
            payload=response.json()
        if not isinstance(payload,dict) or not isinstance(payload.get('output'),list):
            raise ValueError('Invalid response envelope')
        chunks=[]
        for item in payload['output']:
            if not isinstance(item,dict) or not isinstance(item.get('content',[]),list):
                raise ValueError('Invalid output item')
            for content in item.get('content',[]):
                if not isinstance(content,dict): raise ValueError('Invalid content')
                if content.get('type')=='output_text': chunks.append(content.get('text'))
        output=json.loads(''.join(chunks))
        if not isinstance(output,dict) or set(output)!={'order','intro'}:
            raise ValueError('Invalid explanation object')
        order=output['order']
        if not isinstance(order,list) or not all(isinstance(x,str) for x in order) or sorted(order)!=sorted(ids) or output['intro'] not in ('verify_sender','official_channel'): raise ValueError('Invalid evidence selection')
        intros={'verify_sender':'Check with the sender using a contact method you already trust.','official_channel':'For sensitive tasks, use the organization’s official app or a bookmark you already trust.'}
        return {'source':'ai','note':intros[output['intro']],'order':output['order']}
    except (httpx.HTTPError,ValueError,KeyError,TypeError):
        return {**fallback,'note':'AI is unavailable or its response failed validation. Your evidence-based explanation is still complete.'}
