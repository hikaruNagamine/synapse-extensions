"""
GVAR/PVAR collector (inports=0, outports=1).

Reads global variables (``$GVAR0``–``$GVAR63``, ``$PVAR0``–``$PVAR63``) via the
SpeeDBee **DB クエリ** HTTP API (same style as ``POST .../dbquery`` with
``X-hive-api-key``), not ``get_common_variable`` (which does not expose GVAR/PVAR).

Each sampling tick runs one query of the form::

    SELECT $PVAR29, $PVAR28, ... FROM SPDB
    WHERE _TS BETWEEN <from_ns> AND <to_ns>
    ORDER BY _TS DESC LIMIT 1

``from_ns`` / ``to_ns`` are nanosecond timestamps derived from the current
``interval_iteration`` tick (scheduled time and the start of that interval).

**Parameter format**

~~~
{
  "interval_sec": 1,
  "dbquery_url": "http://127.0.0.1:8081/dbquery",
  "api_key": "",
  "query_timeout_sec": 30,
  "variables": [
    {"db_ref": "$GVAR0", "column": "gvar0_val", "label_ja": "例", "description": "任意"}
  ]
}
~~~

| item              | description                                        |
|:--|:--|
| interval_sec      | Sample period in sec (default 1)                    |
| dbquery_url       | DB クエリ POST エンドポイント（例: ``http://host:8081/dbquery``） |
| api_key           | DB クエリ用 **アクセストークン**（ヘッダ ``X-hive-api-key``）。認証必須環境ではフロー編集等で発行したトークンを設定。未設定時はヘッダを送らない |
| query_timeout_sec | クエリタイムアウト（秒、デフォルト 30）             |
| variables         | Array of objects (custom UI), or JSON string thereof |

Each object in ``variables``:

| field       | required | description                                        |
|:--|:--|:--|
| db_ref      | yes      | SQL-style ref: ``$GVARn`` / ``$PVARn`` (``$`` 省略可) |
| column      | yes      | Out-port column name                               |
| label_ja    | no       | Japanese label (metadata only)                     |
| description | no       | Free-text note (metadata only)                     |

**Out-port columns**

One ``STRING`` column per ``variables[].column``; values come from the latest
matching row in the query result. On failure or missing field, inserts empty string.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

import requests

from speedbeesynapse.component.base import DataType, ErrorType, HiveComponentBase, HiveComponentInfo

_GVAR_PVAR_RE = re.compile(r"^\$?(?P<kind>GVAR|PVAR)(?P<num>\d{1,2})$", re.IGNORECASE)
_INVALID_COLUMN = re.compile(r'[\\/*?"<>|\']|\s')

_ConfigError = ErrorType('gvar_pvar_collector_config', 'message')


@dataclass(frozen=True)
class _VariableSpec:
    db_ref: str
    sql_token: str
    column: str
    label_ja: str
    description: str


def _normalize_gvar_pvar_token(token: str) -> str | None:
    m = _GVAR_PVAR_RE.match(token.strip())
    if not m:
        return None
    kind = m.group('kind').upper()
    num = int(m.group('num'))
    if num < 0 or num > 63:
        return None
    return f'{kind}{num}'


def _sql_token_from_db_ref(db_ref: str, api_name: str) -> str:
    s = db_ref.strip()
    if s.startswith('$'):
        return s
    return f'${api_name}'


def _coerce_param_dict(raw: dict | str) -> dict | str:
    if isinstance(raw, str):
        try:
            loaded = json.loads(raw)
        except json.JSONDecodeError:
            return raw
        if isinstance(loaded, dict):
            return loaded
    return raw


def _parse_variable_specs(raw: dict | str) -> tuple[list[_VariableSpec], Any | None]:
    if not isinstance(raw, dict):
        return [], _ConfigError(message='パラメータは JSON オブジェクトである必要があります。')

    raw_list = raw.get('variables')
    if raw_list is None:
        return [], _ConfigError(message='variables が指定されていません。')

    if isinstance(raw_list, str):
        try:
            items = json.loads(raw_list)
        except json.JSONDecodeError as e:
            return [], _ConfigError(message=f'variables の JSON が不正です: {e}')
    elif isinstance(raw_list, list):
        items = raw_list
    else:
        return [], _ConfigError(message='variables は JSON 配列またはその文字列である必要があります。')

    if not items:
        return [], _ConfigError(message='variables に少なくとも 1 要素が必要です。')

    specs: list[_VariableSpec] = []
    seen_columns: set[str] = set()

    for i, item in enumerate(items):
        if not isinstance(item, dict):
            return [], _ConfigError(message=f'variables[{i}] はオブジェクトである必要があります。')

        db_ref = item.get('db_ref')
        column = item.get('column')
        if not db_ref or not isinstance(db_ref, str):
            return [], _ConfigError(message=f'variables[{i}].db_ref は必須の文字列です。')
        if not column or not isinstance(column, str):
            return [], _ConfigError(message=f'variables[{i}].column は必須の文字列です。')

        api_name = _normalize_gvar_pvar_token(db_ref)
        if api_name is None:
            return [], _ConfigError(
                message=f'variables[{i}].db_ref "{db_ref}" は $GVAR0–$GVAR63 または '
                f'$PVAR0–$PVAR63 形式である必要があります。',
            )

        if not column.strip():
            return [], _ConfigError(message=f'variables[{i}].column が空です。')
        if _INVALID_COLUMN.search(column):
            return [], _ConfigError(
                message=f'variables[{i}].column "{column}" に使用できない文字が含まれます。',
            )

        if column in seen_columns:
            return [], _ConfigError(message=f'column 名が重複しています: "{column}"')
        seen_columns.add(column)

        label_ja = item.get('label_ja', '') or ''
        description = item.get('description', '') or ''
        if not isinstance(label_ja, str):
            return [], _ConfigError(message=f'variables[{i}].label_ja は文字列である必要があります。')
        if not isinstance(description, str):
            return [], _ConfigError(message=f'variables[{i}].description は文字列である必要があります。')

        specs.append(
            _VariableSpec(
                db_ref=db_ref.strip(),
                sql_token=_sql_token_from_db_ref(db_ref, api_name),
                column=column,
                label_ja=label_ja,
                description=description,
            ),
        )

    return specs, None


def _interval_ns(raw: dict | str) -> int:
    if isinstance(raw, dict):
        # Prefer interval_sec. interval_ms is kept for backward compatibility.
        if 'interval_sec' in raw:
            sec = float(raw.get('interval_sec', 1))
            return int(max(sec, 0.001) * 1_000_000_000)
        ms = float(raw.get('interval_ms', 1000))
        return int(max(ms, 1.0) * 1_000_000)
    return 1_000_000_000


def _parse_db_client_config(raw: dict) -> tuple[str, str, int, Any | None]:
    url = str(raw.get('dbquery_url', '') or '').strip()
    if not url:
        return '', '', 0, _ConfigError(message='dbquery_url を指定してください。')

    api_key = raw.get('api_key', '') or ''
    if not isinstance(api_key, str):
        return '', '', 0, _ConfigError(message='api_key は文字列である必要があります。')
    api_key = api_key.strip()

    try:
        timeout = int(raw.get('query_timeout_sec', 30))
    except (TypeError, ValueError):
        timeout = 30
    timeout = max(1, min(timeout, 180))

    return url, api_key, timeout, None


def _result_row_to_map(body: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    res = body.get('result')
    if not res or not isinstance(res, dict):
        return out
    records = res.get('records')
    if not records:
        return out
    last = records[-1]
    data = last.get('data')
    if not isinstance(data, list):
        return out
    for item in data:
        if not isinstance(item, dict):
            continue
        name = item.get('name')
        if name is not None:
            out[str(name)] = item.get('value')
    return out


def _lookup_gvar_value(row: dict[str, Any], sql_token: str) -> Any | None:
    """Match API ``name`` field which may be ``$PVAR29`` or ``PVAR29`` etc."""
    candidates = [
        sql_token,
        sql_token.lstrip('$'),
        sql_token.upper(),
        sql_token.lstrip('$').upper(),
    ]
    seen: set[str] = set()
    for c in candidates:
        if c in seen:
            continue
        seen.add(c)
        if c in row:
            return row[c]
    return None


def _value_to_insert_str(value: Any) -> str:
    if value is None:
        return ''
    if isinstance(value, bool):
        return 'true' if value else 'false'
    return str(value)


@HiveComponentInfo(
    uuid='de890e3b-3748-463b-b42b-300dd96eaa9c',
    name='GVAR/PVAR collector',
    inports=0,
    outports=1,
)
class HiveComponent(HiveComponentBase):

    def premain(self, param: dict | str) -> Any | None:
        base = _coerce_param_dict(param)
        if not isinstance(base, dict):
            return _ConfigError(message='パラメータは JSON オブジェクトである必要があります。')

        specs, err = _parse_variable_specs(base)
        if err is not None:
            return err

        url, api_key, timeout, cerr = _parse_db_client_config(base)
        if cerr is not None:
            return cerr

        self._dbquery_url = url
        self._api_key = api_key
        self._query_timeout_sec = timeout

        ordered_unique: list[str] = []
        seen_tok: set[str] = set()
        for s in specs:
            if s.sql_token not in seen_tok:
                seen_tok.add(s.sql_token)
                ordered_unique.append(s.sql_token)

        self._select_list_sql = ', '.join(ordered_unique)

        self._bindings: list[tuple[Any, str]] = []
        for s in specs:
            col = self.out_port1.Column(s.column, DataType.STRING)
            self._bindings.append((col, s.sql_token))

        self._interval_ns = _interval_ns(base)
        self.log.info(
            f'GVAR/PVAR collector initialized: interval_ns={self._interval_ns}, '
            f'dbquery_url={self._dbquery_url}, timeout={self._query_timeout_sec}, '
            f'bindings={len(self._bindings)}'
        )
        self.log.debug(f'GVAR/PVAR select list: {self._select_list_sql}')
        return None

    def _execute_gvar_select(self, from_ns: int, to_ns: int) -> dict[str, Any]:
        query = (
            f'SELECT {self._select_list_sql} FROM SPDB '
            f'WHERE _TS BETWEEN {from_ns} AND {to_ns};'
        )
        self.log.debug(f'GVAR/PVAR query: {query}')
        headers: dict[str, str] = {'Content-Type': 'application/json'}
        if self._api_key:
            headers['X-hive-api-key'] = self._api_key
        payload = {
            'query': query,
            'timeout': self._query_timeout_sec,
            'timestamp_unit': 'nanosecond',
        }
        try:
            resp = requests.post(
                self._dbquery_url,
                headers=headers,
                json=payload,
                timeout=self._query_timeout_sec + 5,
            )
            resp.raise_for_status()
            body = resp.json()
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 401:
                resp_snip = e.response.text[:500] if e.response.text else str(e)
                self.log.warning(
                    f'DB query 401 Unauthorized: '
                    f'コンポーネントパラメータの api_key に、SpeeDBee Synapse の '
                    f'DB クエリ用アクセストークン（X-hive-api-key）を設定してください。'
                    f' URL={self._dbquery_url} 応答={resp_snip}'
                )
            else:
                self.log.warning(f'DB query HTTP error: {e}')
            return {}
        except requests.RequestException as e:
            self.log.warning(f'DB query request failed: {e}')
            return {}
        except ValueError as e:
            self.log.warning(f'DB query JSON decode failed: {e}')
            return {}

        if not body.get('success', True):
            self.log.warning(f'DB query returned success=false: {body}')
            return {}

        row = _result_row_to_map(body)
        self.log.debug(f'GVAR/PVAR query row: {row}')
        return row

    def main(self, _raw_param: dict | str) -> Any | None:
        for ts, _skip in self.interval_iteration(self._interval_ns):
            if not self.is_runnable():
                break
            to_ns = int(ts)
            from_ns = max(0, to_ns - int(self._interval_ns))
            row = self._execute_gvar_select(from_ns, to_ns)
            for col, sql_token in self._bindings:
                raw_val = _lookup_gvar_value(row, sql_token)
                insert_val = _value_to_insert_str(raw_val)
                self.log.debug(f'GVAR/PVAR insert: token={sql_token}, value={insert_val}, ts={ts}')
                col.insert(insert_val, ts)
