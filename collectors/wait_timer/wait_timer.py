"""
Wait timer collector (inports=1, outports=1).

Each time raw data arrives on ``in_port1``, waits ``wait_ms`` milliseconds,
then inserts ``True`` into the ``trigger`` column on ``out_port1``.

**Parameter format**

~~~
{
  "wait_ms": 1000
}
~~~

| item    | description              |
|:--|:--|
| wait_ms | Delay after input (ms)   |

**Out-port columns**

| Column  | Data-type | Description        |
|:--|:--|:--|
| trigger | BOOLEAN   | Event pulse (true) |
"""
from __future__ import annotations

from speedbeesynapse.component.base import DataType, HiveComponentBase, HiveComponentInfo


class Param:

    """Parameter class."""

    def __init__(self, wait_ns: int) -> None:
        self.wait_ns = wait_ns


@HiveComponentInfo(
    uuid='90d5175d-1cd9-4a69-82ae-8c0a05bae0b8',
    name='Wait timer',
    inports=1,
    outports=1,
)
class HiveComponent(HiveComponentBase):

    """Component main class."""

    def premain(self, _param: dict | str) -> None:
        self.trigger = self.out_port1.Column('trigger', DataType.BOOLEAN)

    def main(self, raw_param: dict | str) -> None:
        param = self.parse_param(raw_param)
        poll_ns = 1_000_000

        with self.in_port1.ContinuousReader(start=self.get_timestamp()) as reader:
            while self.is_runnable():
                window_data = reader.read()
                if not window_data:
                    continue
                n = len(window_data.records)
                if n == 0 and window_data.event_id >= 1:
                    n = 1
                for _ in range(n):
                    if not self._sleep_ns(param.wait_ns, poll_ns):
                        return
                    if not self.is_runnable():
                        return
                    self.trigger.insert(True, self.get_timestamp())

    def _sleep_ns(self, duration_ns: int, poll_ns: int) -> bool:
        if duration_ns <= 0:
            return self.is_runnable()
        end = self.get_timestamp() + duration_ns
        while self.is_runnable():
            if self.get_timestamp() >= end:
                return True
            for _ in self.interval_iteration(poll_ns):
                break
        return False

    def parse_param(self, param: dict | str) -> Param:
        if isinstance(param, dict):
            wait_ms = int(param.get('wait_ms', 1000))
            return Param(wait_ms * 1_000_000)
        return Param(1_000_000_000)
