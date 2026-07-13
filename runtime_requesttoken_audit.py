import hashlib
import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from PySide6.QtCore import QTimer

from src.brokers import broker_manager
from src.brokers.fivepaisa.auth_service import FivePaisaAuthService
from src.brokers.fivepaisa.broker_client import FivePaisaBrokerClient

OUT = Path('d:/Projects/ASG/logs/requesttoken_audit.json')
OUT.write_text('{}', encoding='utf-8')
state = {
    'raw_callback_url': '',
    'raw_request_token': '',
    'request_token_length': 0,
    'sha256_after_extraction': '',
    'sha256_before_getaccesstoken': '',
    'hashes_identical': None,
    'transform_checks': {},
}


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def _persist() -> None:
    OUT.write_text(json.dumps(state, indent=2), encoding='utf-8')


orig_build = FivePaisaBrokerClient._build_callback_handler
orig_reauth = FivePaisaBrokerClient.reauthenticate_from_request_token
orig_exchange = FivePaisaAuthService.exchange_request_token


def wrapped_build(self, callback_state, host, port, callback_path):
    handler = orig_build(self, callback_state, host, port, callback_path)
    original_do_get = handler.do_GET

    def audited_do_get(handler_self):
        parsed = urlparse(handler_self.path)
        token_values = parse_qs(parsed.query).get('RequestToken', [])
        token = token_values[0] if token_values else ''
        raw_callback_url = f'http://{host}:{port}{handler_self.path}'
        state['raw_callback_url'] = raw_callback_url
        state['raw_request_token'] = token
        state['request_token_length'] = len(token)
        state['sha256_after_extraction'] = _sha(token) if token else ''
        state['transform_checks'] = {
            'urlparse_parse_qs_value_equals_passed_token': True,
            'strip_changes_value': token != token.strip(),
            'url_decoding_changes_value': '%25' in handler_self.path or '%2B' in handler_self.path or '%2F' in handler_self.path,
            'replace_used': False,
            'split_used_on_token': False,
            'regex_used': False,
            'serialization_used_before_exchange': False,
        }
        _persist()
        return original_do_get(handler_self)

    handler.do_GET = audited_do_get
    return handler


def wrapped_reauth(self, request_token: str):
    state['sha256_before_getaccesstoken'] = _sha(request_token) if request_token else ''
    state['hashes_identical'] = state['sha256_after_extraction'] == state['sha256_before_getaccesstoken']
    state['transform_checks']['token_passed_to_reauthenticate_equals_extracted'] = request_token == state['raw_request_token']
    _persist()
    return orig_reauth(self, request_token)


def wrapped_exchange(self, request_token: str):
    state['sha256_before_getaccesstoken'] = _sha(request_token) if request_token else ''
    state['hashes_identical'] = state['sha256_after_extraction'] == state['sha256_before_getaccesstoken']
    state['transform_checks']['token_passed_to_exchange_equals_extracted'] = request_token == state['raw_request_token']
    _persist()
    return orig_exchange(self, request_token)


FivePaisaBrokerClient._build_callback_handler = wrapped_build
FivePaisaBrokerClient.reauthenticate_from_request_token = wrapped_reauth
FivePaisaAuthService.exchange_request_token = wrapped_exchange

from src.app import create_app

app = create_app()
QTimer.singleShot(6000, broker_manager.connect)
raise SystemExit(app.run())
