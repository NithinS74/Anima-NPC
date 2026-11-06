import hashlib
import json
from pathlib import Path
import struct
from types import SimpleNamespace
import zipfile

import pytest

from scripts import setup_skyrim as install


def game_tree(tmp_path, version="1.7.104.0"):
    game=tmp_path/'game'; (game/'Data/SKSE/Plugins').mkdir(parents=True)
    (game/'Data/Skyrim.esm').touch(); (game/'SkyrimSE.exe').touch(); (game/'skse64_loader.exe').touch()
    (game/'Data/SKSE/Plugins'/('versionlib-'+version.replace('.','-')+'.bin')).write_bytes(struct.pack('<I',install.RUNTIMES[version]))
    return game


def mod_zip(path, *, broken=False):
    path.parent.mkdir(parents=True,exist_ok=True)
    dll=b'controlled DLL fixture'
    with zipfile.ZipFile(path,'w') as archive:
        archive.writestr('SKSE/Plugins/AnimaConnector.dll',dll)
        archive.writestr('SKSE/Plugins/AnimaConnector.ini','[Connection]\nPort=8768\nPushToTalkKey=66\n')
        archive.writestr('AnimaConnector/build.json',json.dumps({'target_runtimes':list(install.RUNTIMES),
            'dll_sha256':'bad' if broken else hashlib.sha256(dll).hexdigest()}))
    return dll


@pytest.mark.parametrize('version',list(install.RUNTIMES))
def test_installation_checks_exact_runtime_and_library(tmp_path,version):
    game=game_tree(tmp_path,version)
    assert install.check_game(game,lambda _:version)==version
    with pytest.raises(ValueError,match='unsupported'):
        install.check_game(game,lambda _:'1.6.1170.0')
    library=next((game/'Data/SKSE/Plugins').glob('*.bin'));library.write_bytes(b'bad')
    with pytest.raises(ValueError,match='Address Library'): install.check_game(game,lambda _:version)


def test_mod_install_checks_hash_preserves_hotkeys_and_backs_up_old_dll(tmp_path):
    game=game_tree(tmp_path);package=tmp_path/'mod.zip';dll=mod_zip(package)
    destination=game/'Data/SKSE/Plugins'
    (destination/'AnimaConnector.dll').write_bytes(b'old')
    (destination/'AnimaConnector.ini').write_text('[Connection]\nPort=8768\nPushToTalkKey=70\n')
    install.install_mod(game,package,'1.7.104.0',8769)
    assert (destination/'AnimaConnector.dll').read_bytes()==dll
    assert (destination/'AnimaConnector.dll.anima-backup').read_bytes()==b'old'
    assert 'pushtotalkkey = 70' in (destination/'AnimaConnector.ini').read_text()
    assert 'port = 8769' in (destination/'AnimaConnector.ini').read_text()
    mod_zip(package,broken=True)
    with pytest.raises(ValueError,match='hash'):install.install_mod(game,package,'1.7.104.0',8768)
    assert (destination/'AnimaConnector.dll').read_bytes()==dll


def provider_files(root):
    directory=root/'configs/providers';directory.mkdir(parents=True)
    source=Path(__file__).parents[2]/'configs/providers'
    for name in ['gemini.yaml','openrouter.yaml']:(directory/name).write_bytes((source/name).read_bytes())


def test_missing_keys_never_silently_select_scripted_provider(tmp_path,monkeypatch):
    provider_files(tmp_path)
    for key in ['NPC_LLM_MODEL','NPC_LLM_API_KEY','GEMINI_API_KEY','OPENROUTER_API_KEY']:
        monkeypatch.delenv(key,raising=False)
    with pytest.raises(ValueError,match='not configured'):install.choose_provider(tmp_path,None)


def test_setup_prepares_full_path_then_installs_after_regression(tmp_path,monkeypatch):
    from scripts import chatterbox_voices
    game=game_tree(tmp_path);dll=mod_zip(tmp_path/'mod/AnimaConnector.zip')
    provider_files(tmp_path)
    for key in ['NPC_LLM_MODEL','NPC_LLM_API_KEY','GEMINI_API_KEY','OPENROUTER_API_KEY','NPC_LLM_BASE_URL']:
        monkeypatch.delenv(key,raising=False)
    (tmp_path/'.env').write_text('GEMINI_API_KEY=test-key\nNPC_LLM_MODEL=fixture-model\n')
    config=tmp_path/'configs/skyrim/connector.example.json';config.parent.mkdir(parents=True)
    config.write_text(json.dumps({'game_directory':'old','provider_profile':'configs/providers/offline.yaml','port':8768}))
    monkeypatch.setattr(install.shutil,'which',lambda _: 'ollama')
    def references(root, game_path):
        assert game_path==game
        (root/'data/tts').mkdir(parents=True)
        return 2
    monkeypatch.setattr(chatterbox_voices,'prepare_voices',references)
    calls=[]
    def run(args,**kwargs):
        calls.append(args)
        if args[-3:]==['-m','pytest','-q']:
            assert not (game/'Data/SKSE/Plugins/AnimaConnector.dll').exists()
        return SimpleNamespace(returncode=0)
    install.setup(tmp_path,game,run=run,version_reader=lambda _:'1.7.104.0')
    assert ['ollama','pull','qwen2.5vl:3b'] in calls
    assert any(args[-3:]==['-m','npc.adapters.skyrim.whisper','--prepare'] for args in calls)
    assert any(args[-3:]==['-m','npc.output.chatterbox','--prepare'] for args in calls)
    raw=json.loads(config.with_name('connector.json').read_text())
    assert raw['provider_profile']=='configs/providers/gemini.yaml'
    assert raw['attach_visual_reference'] is True and raw['cv_url']=='http://127.0.0.1:8000'
    assert (game/'Data/SKSE/Plugins/AnimaConnector.dll').read_bytes()==dll
    assert (tmp_path/'data/tts/.chatterbox-ready.json').is_file()
