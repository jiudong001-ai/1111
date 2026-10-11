import asyncio,json
from datetime import date
import httpx,pytest
from daily_card_generator import DailyCardGenerator
from daily_ai import generate

def test_missing_key_does_not_call(tmp_path,monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY',raising=False)
    with pytest.raises(ValueError,match='OpenAI API'):asyncio.run(generate(date(2026,10,12),1,tmp_path/'ledger'))

def test_structured_copy_and_limit(tmp_path,monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY','fake-test-key')
    monkeypatch.setenv('OPENAI_DAILY_CALL_LIMIT','1')
    d=DailyCardGenerator().draft(date(2026,10,12))
    copy={k:d[k] for k in ('headline','message','love','style','affirmation')}
    def handler(request):
        body=json.loads(request.content)
        assert body['model']=='gpt-6-luna' and body['store'] is False
        assert body['max_output_tokens']==600
        assert 'fake-test-key' not in request.content.decode()
        return httpx.Response(200,json={'status':'completed','output':[{'content':[{'type':'output_text','text':json.dumps(copy)}]}]})
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            result=await generate(date(2026,10,12),1,tmp_path/'ledger',client)
            assert result['remaining']==0 and result['draft']['message']==copy['message']
            with pytest.raises(ValueError,match='次数'):await generate(date(2026,10,12),2,tmp_path/'ledger',client)
    asyncio.run(run())

