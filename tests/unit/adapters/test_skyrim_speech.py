import asyncio
import io
import json
import wave
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from npc.adapters.skyrim.speech import WindowsSpeech, SpeechFailure, SynthesisInput, create_speech_app


def audio(seconds=.1):
    out=io.BytesIO()
    with wave.open(out,"wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000); w.writeframes(b"\0\0"*int(seconds*16000))
    return out.getvalue()


def test_worker_passes_text_as_json_and_removes_files(tmp_path):
    calls=[]
    class Process:
        returncode=0
        async def communicate(self):return b'{"status":"ok"}',None
    async def launch(*args,**kwargs):
        request=Path(args[-1]); data=json.loads(request.read_text()); calls.append((args,data))
        Path(data["output"]).write_bytes(audio()); return Process()
    engine=WindowsSpeech(tmp_path,launch=launch)
    raw=asyncio.run(engine.synthesize(SynthesisInput(request_id="a",text='Hello; $(command) "friend"')))
    assert raw==audio()
    assert calls[0][1]["text"]=='Hello; $(command) "friend"'
    assert all('$(command)' not in part for part in calls[0][0])
    assert list(tmp_path.iterdir())==[] and not engine.busy


@pytest.mark.parametrize("cancel",[False,True])
def test_worker_timeout_and_cancellation_kill_before_temp_cleanup(tmp_path,cancel):
    processes=[]
    class Process:
        returncode=None
        killed=False
        async def communicate(self):await asyncio.sleep(10)
        def kill(self):self.killed=True
        async def wait(self):self.returncode=-1
    async def launch(*args,**kwargs):p=Process();processes.append(p);return p
    async def run():
        engine=WindowsSpeech(tmp_path,timeout_s=.01,launch=launch)
        task=asyncio.create_task(engine.synthesize(SynthesisInput(request_id="a",text="Hello")))
        if cancel:
            while not processes:await asyncio.sleep(0)
            task.cancel()
        with pytest.raises(asyncio.CancelledError if cancel else SpeechFailure):await task
        assert processes[0].killed and not engine.busy and list(tmp_path.iterdir())==[]
    asyncio.run(run())


def test_microphone_validation_and_busy_rejection(tmp_path):
    engine=WindowsSpeech(tmp_path);engine.busy=True
    async def run():
        with pytest.raises(ValueError):await engine.transcribe(b"invalid")
        with pytest.raises(SpeechFailure,match="microphone_audio_limit"):await engine.transcribe(audio(17))
        with pytest.raises(SpeechFailure,match="speech_busy"):await engine.synthesize(SynthesisInput(request_id="a",text="Hello"))
    asyncio.run(run())


def test_speech_routes_bound_input_and_report_real_failures():
    class Engine:
        async def _run(self,op):return {"voices":["David"],"recognizers":["en-US"]}
        async def synthesize(self,req):return audio()
        async def transcribe(self,raw):
            if raw!=audio():raise SpeechFailure("invalid_audio")
            return {"text":"Hello","confidence":.9}
    with TestClient(create_speech_app(Engine())) as c:
        assert c.get('/health').json()['status']=='ready'
        assert c.post('/tts',json={'request_id':'a','text':'Hello'}).content==audio()
        assert c.post('/tts',json={'request_id':'a','text':'x'*601}).status_code==422
        assert c.post('/tts',content=b'x'*17000,headers={'content-type':'application/json'}).status_code==413
        assert c.post('/stt',content=audio()).status_code==415
        assert c.post('/stt',content=audio(),headers={'content-type':'audio/wav'}).json()['text']=='Hello'
        assert c.post('/stt',content=b'bad',headers={'content-type':'audio/wav'}).status_code==503


def test_speech_service_rejects_non_loopback():
    with TestClient(create_speech_app(None),client=('198.51.100.1',4444)) as c:
        assert c.get('/health').status_code==403
