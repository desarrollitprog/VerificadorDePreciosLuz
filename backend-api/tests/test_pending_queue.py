"""
Pruebas unitarias para PendingCommandQueue (FASE 15 - Lote 2).
Usa FakeRedis en memoria para evitar dependencia externa.
"""
import sys
import os
import json
import time
import asyncio
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class FakeRedis:
    """Simula los métodos de redis.asyncio.Redis que usa PendingCommandQueue."""

    def __init__(self):
        self._lists: dict[str, list] = {}
        self._strings: dict[str, str] = {}
        self._sets: dict[str, set] = {}
        self._closed = False

    async def llen(self, key: str) -> int:
        return len(self._lists.get(key, []))

    async def rpush(self, key: str, *values: str) -> int:
        if key not in self._lists:
            self._lists[key] = []
        self._lists[key].extend(values)
        return len(self._lists[key])

    async def lpush(self, key: str, *values: str) -> int:
        if key not in self._lists:
            self._lists[key] = []
        for v in reversed(values):
            self._lists[key].insert(0, v)
        return len(self._lists[key])

    async def lmove(self, src: str, dst: str, wherefrom: str, whereto: str) -> str | None:
        src_list = self._lists.get(src, [])
        if not src_list:
            return None
        val = src_list.pop(0)
        if dst not in self._lists:
            self._lists[dst] = []
        self._lists[dst].append(val)
        return val

    async def lrem(self, key: str, count: int, value: str) -> int:
        lst = self._lists.get(key, [])
        before = len(lst)
        if count == 1:
            try:
                lst.remove(value)
            except ValueError:
                pass
        elif count == 0:
            self._lists[key] = [v for v in lst if v != value]
        return before - len(self._lists.get(key, lst))

    async def lrange(self, key: str, start: int, stop: int) -> list:
        lst = self._lists.get(key, [])
        if stop == -1:
            return lst[start:]
        return lst[start:stop]

    async def delete(self, key: str) -> int:
        found = 0
        if key in self._lists:
            del self._lists[key]
            found += 1
        if key in self._strings:
            del self._strings[key]
            found += 1
        if key in self._sets:
            del self._sets[key]
            found += 1
        return found

    async def set(self, key: str, value: str, ex: int | None = None) -> bool:
        self._strings[key] = value
        return True

    async def get(self, key: str) -> str | None:
        return self._strings.get(key)
    
    async def sadd(self, key: str, value: str) -> int:
        if key not in self._sets:
            self._sets[key] = set()
        if value in self._sets[key]:
            return 0
        self._sets[key].add(value)
        return 1
    
    async def expire(self, key: str, seconds: int) -> bool:
        return True

    async def ping(self) -> bool:
        return True

    async def close(self) -> None:
        self._closed = True

    def scan_iter(self, match: str | None = None):
        """Devuelve un async generator que itera sobre keys de lists, strings y sets."""
        async def _scan():
            all_keys = set(self._lists.keys()) | set(self._strings.keys()) | set(self._sets.keys())
            if match:
                import fnmatch
                for k in sorted(all_keys):
                    if fnmatch.fnmatch(k, match):
                        yield k
            else:
                for k in sorted(all_keys):
                    yield k
        return _scan()


class TestPendingCommandQueue:
    """Pruebas de PendingCommandQueue con FakeRedis."""

    @classmethod
    def setup_class(cls):
        cls.device_id = "test-device-001"

    def _make_queue(self):
        from app.services.pending_queue import PendingCommandQueue
        fake = FakeRedis()
        q = PendingCommandQueue(redis=fake)
        return q, fake

    async def test_enqueue_dequeue(self):
        """L2.1: Encolar y desencolar con LMOVE atómico."""
        q, fake = self._make_queue()
        msg = {"command": "WIPE_AND_RESYNC", "device_id": self.device_id}
        result = await q.enqueue(self.device_id, msg)
        assert result is True

        queue_key = f"{q.QUEUE_PREFIX}:{self.device_id}"
        assert await fake.llen(queue_key) == 1

        dequeued = await q.dequeue(self.device_id)
        assert dequeued is not None
        assert dequeued["command"] == "WIPE_AND_RESYNC"
        assert "enqueued_at" in dequeued

        inflight_key = f"{q.QUEUE_PREFIX}:{self.device_id}:{q.INFLIGHT_SUFFIX}"
        assert await fake.llen(inflight_key) == 1
        assert await fake.llen(queue_key) == 0

    async def test_dequeue_empty_returns_none(self):
        """Desencolar cola vacía retorna None."""
        q, _ = self._make_queue()
        result = await q.dequeue("nonexistent-device")
        assert result is None

    async def test_enqueue_queue_full(self):
        """L2.1: Cola llena (>= MAX_QUEUE_PER_DEVICE) retorna False."""
        q, _ = self._make_queue()
        limit = q.MAX_QUEUE_PER_DEVICE  # 100
        for i in range(limit):
            ok = await q.enqueue(self.device_id, {"seq": i})
            assert ok is True, f"Fallo al encolar mensaje {i}"

        overflow = await q.enqueue(self.device_id, {"seq": limit})
        assert overflow is False

    async def test_confirm_success(self):
        """L2.2: Confirmar mensaje lo remueve de inflight."""
        q, fake = self._make_queue()
        msg = {"command": "REINICIAR", "device_id": self.device_id}
        await q.enqueue(self.device_id, msg)
        raw = json.dumps({**msg, "enqueued_at": time.time()})

        inflight_key = f"{q.QUEUE_PREFIX}:{self.device_id}:{q.INFLIGHT_SUFFIX}"
        await fake.rpush(inflight_key, raw)

        ok = await q.confirm(self.device_id, raw)
        assert ok is True
        assert await fake.llen(inflight_key) == 0

    async def test_confirm_nonexistent(self):
        """Confirmar mensaje inexistente retorna False."""
        q, _ = self._make_queue()
        ok = await q.confirm("nonexistent", '{"command":"TEST"}')
        assert ok is False

    async def test_recover_inflight(self):
        """L2.2: Recuperar inflight mueve todos de vuelta a queue."""
        q, fake = self._make_queue()
        inflight_key = f"{q.QUEUE_PREFIX}:{self.device_id}:{q.INFLIGHT_SUFFIX}"
        queue_key = f"{q.QUEUE_PREFIX}:{self.device_id}"
        for i in range(3):
            await fake.rpush(inflight_key, json.dumps({"seq": i}))
        assert await fake.llen(inflight_key) == 3

        recovered = await q.recover_inflight(self.device_id)
        assert recovered == 3
        assert await fake.llen(inflight_key) == 0
        assert await fake.llen(queue_key) == 3

    async def test_recover_inflight_empty(self):
        """Recuperar inflight vacío es no-op."""
        q, _ = self._make_queue()
        recovered = await q.recover_inflight(self.device_id)
        assert recovered == 0

    async def test_flush_all_to_device_success(self):
        """L2.2: flush_all_to_device envía todos y confirma."""
        q, _ = self._make_queue()
        n = 5
        for i in range(n):
            await q.enqueue(self.device_id, {"command": "TEST", "seq": i})

        sent = []

        async def fake_send(msg):
            sent.append(msg)
            return True

        delivered = await q.flush_all_to_device(self.device_id, fake_send)
        assert delivered == n
        assert len(sent) == n
        for i in range(n):
            assert sent[i]["seq"] == i

    async def test_flush_all_to_device_partial_failure(self):
        """L2.2: Fallo en send re-encola y detiene el flush."""
        q, _ = self._make_queue()
        for i in range(5):
            await q.enqueue(self.device_id, {"command": "TEST", "seq": i})

        sent = []

        async def fake_send(msg):
            sent.append(msg)
            if msg["seq"] == 2:
                return False
            return True

        delivered = await q.flush_all_to_device(self.device_id, fake_send)
        assert delivered == 2
        assert len(sent) == 3

        # El mensaje que falló debe re-encolarse
        remaining_key = f"{q.QUEUE_PREFIX}:{self.device_id}"
        remaining = await q.redis.llen(remaining_key)
        assert remaining >= 1

    async def test_flush_all_to_device_crash_re_enqueue(self):
        """L2.2: Excepción en send re-encola el mensaje."""
        q, _ = self._make_queue()
        await q.enqueue(self.device_id, {"command": "TEST", "seq": 0})
        await q.enqueue(self.device_id, {"command": "TEST", "seq": 1})

        calls = 0

        async def fake_send(msg):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise RuntimeError("connection lost")
            return True

        delivered = await q.flush_all_to_device(self.device_id, fake_send)
        assert delivered == 1

    async def test_get_queue_size(self):
        """L2: Estadísticas de cola."""
        q, fake = self._make_queue()
        await q.enqueue(self.device_id, {"command": "TEST"})
        inflight_key = f"{q.QUEUE_PREFIX}:{self.device_id}:{q.INFLIGHT_SUFFIX}"
        await fake.rpush(inflight_key, json.dumps({"command": "TEST_INFLIGHT"}))

        stats = await q.get_queue_size(self.device_id)
        assert stats["pending"] == 1
        assert stats["inflight"] == 1
        assert stats["total"] == 2

    async def test_get_all_stats(self):
        """L2: Estadísticas multi-dispositivo."""
        q, _ = self._make_queue()
        for dev in ["dev-a", "dev-b"]:
            await q.enqueue(dev, {"command": "TEST"})

        stats = await q.get_all_stats()
        assert "dev-a" in stats
        assert "dev-b" in stats
        assert stats["dev-a"]["pending"] == 1
        assert stats["dev-b"]["pending"] == 1

    async def test_cleanup_old_messages(self):
        """L2.3: Mensajes viejos (>24h) se eliminan."""
        q, fake = self._make_queue()
        old_cutoff = time.time() - 90000
        new_time = time.time()

        old_key = f"{q.QUEUE_PREFIX}:{self.device_id}"
        old_msg = json.dumps({"command": "OLD", "enqueued_at": old_cutoff})
        new_msg = json.dumps({"command": "NEW", "enqueued_at": new_time})
        await fake.rpush(old_key, old_msg)
        await fake.rpush(old_key, new_msg)

        cleaned = await q.cleanup_old_messages()
        assert cleaned == 1

        remaining = await fake.lrange(old_key, 0, -1)
        assert len(remaining) == 1
        parsed = json.loads(remaining[0])
        assert parsed["command"] == "NEW"

    async def test_cleanup_no_old_messages(self):
        """Sin mensajes viejos, cleanup retorna 0."""
        q, _ = self._make_queue()
        now = time.time()
        for i in range(3):
            await q.enqueue(self.device_id, {"seq": i, "enqueued_at": now})
        cleaned = await q.cleanup_old_messages()
        assert cleaned == 0

    async def test_cleanup_skips_inflight_keys(self):
        """cleanup skipea keys que terminan en :inflight."""
        q, fake = self._make_queue()
        inflight_key = f"{q.QUEUE_PREFIX}:{self.device_id}:{q.INFLIGHT_SUFFIX}"
        old = json.dumps({"command": "OLD", "enqueued_at": time.time() - 90000})
        await fake.rpush(inflight_key, old)
        cleaned = await q.cleanup_old_messages()
        assert cleaned == 0

    async def test_consume_pending_banner(self):
        """L2.4: Consumir banner pendiente legacy."""
        q, fake = self._make_queue()
        banner_key = f"{q.PENDING_BANNER_PREFIX}:{self.device_id}"
        banner_data = json.dumps({"command": "BANNER_INICIADO", "id": 1})
        await fake.set(banner_key, banner_data)

        result = await q.consume_pending_banner(self.device_id)
        assert result is not None
        assert result["command"] == "BANNER_INICIADO"
        assert result["id"] == 1

        # Segunda llamada retorna None (ya se consumió)
        result2 = await q.consume_pending_banner(self.device_id)
        assert result2 is None

    async def test_set_check_pending_sync(self):
        """L3: Flag sync pendiente."""
        q, _ = self._make_queue()
        await q.set_pending_sync(self.device_id)
        assert await q.check_pending_sync(self.device_id) is True
        assert await q.check_pending_sync(self.device_id) is False

    async def test_set_check_pending_reboot(self):
        """L3: Flag REINICIAR pendiente."""
        q, _ = self._make_queue()
        payload = {"command": "REINICIAR", "reason": "update"}
        await q.set_pending_reboot(self.device_id, payload)
        result = await q.check_pending_reboot(self.device_id)
        assert result is not None
        assert result["command"] == "REINICIAR"
        assert result["reason"] == "update"
        assert await q.check_pending_reboot(self.device_id) is None

    async def test_enqueue_malformed_dequeue(self):
        """Mensaje corrupto en dequeue se remueve de inflight."""
        q, fake = self._make_queue()
        queue_key = f"{q.QUEUE_PREFIX}:{self.device_id}"
        inflight_key = f"{q.QUEUE_PREFIX}:{self.device_id}:{q.INFLIGHT_SUFFIX}"
        await fake.rpush(queue_key, "not-valid-json")

        result = await q.dequeue(self.device_id)
        assert result is None
        assert await fake.llen(queue_key) == 0
        assert await fake.llen(inflight_key) == 0

    # ─────────────────────────────
    # DLQ Tests (L3.4)
    # ─────────────────────────────

    async def test_flush_to_dlq_after_max_retries(self):
        """L3.4: Mensaje movido a DLQ tras MAX_RETRIES intentos fallidos."""
        q, _ = self._make_queue()
        msg = {"command": "TEST", "seq": 1}
        await q.enqueue(self.device_id, msg)

        attempts = 0

        async def always_fail(msg):
            nonlocal attempts
            attempts += 1
            return False

        delivered = await q.flush_all_to_device(self.device_id, always_fail)
        assert delivered == 0
        # Primer fallo: retry_count=1, re-encolado
        assert await q.get_dlq_size(self.device_id) == 0
        assert attempts == 1

        # Fallar 4 veces más (total 5 = MAX_RETRIES)
        for i in range(q.MAX_RETRIES - 1):
            await q.flush_all_to_device(self.device_id, always_fail)

        assert attempts == q.MAX_RETRIES
        assert await q.get_dlq_size(self.device_id) == 1

        # Verificar que el mensaje está en DLQ
        dlq_items = await q.get_all_dlq(self.device_id)
        assert len(dlq_items) == 1
        assert dlq_items[0]["command"] == "TEST"
        assert dlq_items[0]["retry_count"] == q.MAX_RETRIES - 1
        assert "moved_to_dlq_at" in dlq_items[0]

    async def test_flush_to_dlq_after_exception(self):
        """L3.4: Excepción también cuenta como intento y va a DLQ."""
        q, _ = self._make_queue()
        msg = {"command": "TEST"}
        await q.enqueue(self.device_id, msg)

        async def always_crash(msg):
            raise RuntimeError("crash")

        # Primer intento: retry_count=0 -> se incrementa a 1, re-encola
        await q.flush_all_to_device(self.device_id, always_crash)
        assert await q.get_dlq_size(self.device_id) == 0

        # Fallar 4 veces más
        for _ in range(q.MAX_RETRIES - 1):
            await q.flush_all_to_device(self.device_id, always_crash)

        assert await q.get_dlq_size(self.device_id) == 1

    async def test_get_dlq_size_empty(self):
        """L3.4: DLQ vacía retorna 0."""
        q, _ = self._make_queue()
        size = await q.get_dlq_size(self.device_id)
        assert size == 0

    async def test_get_all_dlq_empty(self):
        """L3.4: get_all_dlq de DLQ vacía retorna []."""
        q, _ = self._make_queue()
        items = await q.get_all_dlq(self.device_id)
        assert items == []

    async def test_cleanup_old_dlq(self):
        """L3.4: DLQ >24h se limpia."""
        q, fake = self._make_queue()
        dlq_key = q._dlq_key(self.device_id)
        old_msg = json.dumps({"command": "OLD", "moved_to_dlq_at": time.time() - 90000})
        new_msg = json.dumps({"command": "NEW", "moved_to_dlq_at": time.time()})
        await fake.rpush(dlq_key, old_msg)
        await fake.rpush(dlq_key, new_msg)

        cleaned = await q.cleanup_old_dlq()
        assert cleaned == 1

        remaining = await q.get_all_dlq(self.device_id)
        assert len(remaining) == 1
        assert remaining[0]["command"] == "NEW"

    async def test_cleanup_old_dlq_empty(self):
        """L3.4: cleanup_old_dlq sin viejos retorna 0."""
        q, fake = self._make_queue()
        dlq_key = q._dlq_key(self.device_id)
        await fake.rpush(dlq_key, json.dumps({"command": "NEW", "moved_to_dlq_at": time.time()}))
        cleaned = await q.cleanup_old_dlq()
        assert cleaned == 0

    async def test_flush_success_resets_dlq_not_affected(self):
        """L3.4: Mensajes exitosos no afectan DLQ."""
        q, _ = self._make_queue()
        msg = {"command": "HELLO"}
        await q.enqueue(self.device_id, msg)

        async def succeed(msg):
            return True

        delivered = await q.flush_all_to_device(self.device_id, succeed)
        assert delivered == 1
        assert await q.get_dlq_size(self.device_id) == 0

    # ─────────────────────────────
    # Dedup Tests (L4)
    # ─────────────────────────────

    async def test_enqueue_dedup_wipe_duplicates(self):
        """L4: WIPE_AND_RESYNC duplicado se omite en la cola (SADD atómico)."""
        q, fake = self._make_queue()
        msg = {"command": "WIPE_AND_RESYNC"}
        ok1 = await q.enqueue(self.device_id, msg)
        assert ok1 is True
        dedup_key = f"device:dedup:{self.device_id}:WIPE_AND_RESYNC"
        assert dedup_key in fake._sets  # SADD key creada
        ok2 = await q.enqueue(self.device_id, msg)
        assert ok2 is True  # faux-success (dedup por SADD)
        queue_key = f"{q.QUEUE_PREFIX}:{self.device_id}"
        assert await q.redis.llen(queue_key) == 1  # solo 1, no 2

    async def test_enqueue_dedup_reboot_duplicates(self):
        """L4: REINICIAR duplicado se omite en la cola (SADD atómico)."""
        q, fake = self._make_queue()
        msg = {"command": "REINICIAR", "reason": "update"}
        ok1 = await q.enqueue(self.device_id, msg)
        assert ok1 is True
        dedup_key = f"device:dedup:{self.device_id}:REINICIAR"
        assert dedup_key in fake._sets  # SADD key creada
        ok2 = await q.enqueue(self.device_id, msg)
        assert ok2 is True  # faux-success (dedup por SADD)
        queue_key = f"{q.QUEUE_PREFIX}:{self.device_id}"
        assert await q.redis.llen(queue_key) == 1

    async def test_enqueue_dedup_non_critical(self):
        """L4: BANNER_* duplicado SÍ se encola (no está en DEDUP_COMMANDS)."""
        q, _ = self._make_queue()
        msg = {"command": "BANNER_INICIADO", "id": 1}
        ok1 = await q.enqueue(self.device_id, msg)
        assert ok1 is True
        ok2 = await q.enqueue(self.device_id, msg)
        assert ok2 is True
        queue_key = f"{q.QUEUE_PREFIX}:{self.device_id}"
        assert await q.redis.llen(queue_key) == 2  # ambos se encolan

    async def test_enqueue_dedup_diff_device(self):
        """L4: Dedup es por dispositivo, no global."""
        q, _ = self._make_queue()
        msg = {"command": "REINICIAR"}
        await q.enqueue("dev-a", msg)
        await q.enqueue("dev-b", msg)  # otro dispositivo, NO es duplicado
        queue_a = f"{q.QUEUE_PREFIX}:dev-a"
        queue_b = f"{q.QUEUE_PREFIX}:dev-b"
        assert await q.redis.llen(queue_a) == 1
        assert await q.redis.llen(queue_b) == 1

    # ─────────────────────────────
    # Cleanup Orphan Flags Tests (L4.3)
    # ─────────────────────────────

    async def test_cleanup_orphan_flags_removes_stale(self):
        """L4.3: Flags de dispositivos inexistentes se eliminan."""
        q, fake = self._make_queue()
        await fake.set(f"{q.PENDING_SYNC_PREFIX}:ghost-device", "true")
        await fake.set(f"{q.PENDING_REBOOT_PREFIX}:ghost-device", '{"command":"REINICIAR"}')
        active = {"real-device"}
        cleaned = await q.cleanup_orphan_flags(active)
        assert cleaned == 2
        assert await fake.get(f"{q.PENDING_SYNC_PREFIX}:ghost-device") is None
        assert await fake.get(f"{q.PENDING_REBOOT_PREFIX}:ghost-device") is None

    async def test_cleanup_orphan_flags_preserves_active(self):
        """L4.3: Flags de dispositivos activos se conservan."""
        q, fake = self._make_queue()
        await fake.set(f"{q.PENDING_SYNC_PREFIX}:active-dev", "true")
        await fake.set(f"{q.PENDING_REBOOT_PREFIX}:active-dev", '{"command":"REINICIAR"}')
        active = {"active-dev", "other-dev"}
        cleaned = await q.cleanup_orphan_flags(active)
        assert cleaned == 0
        assert await fake.get(f"{q.PENDING_SYNC_PREFIX}:active-dev") == "true"
        assert await fake.get(f"{q.PENDING_REBOOT_PREFIX}:active-dev") == '{"command":"REINICIAR"}'

    async def test_cleanup_orphan_flags_no_flags(self):
        """L4.3: Sin flags, cleanup retorna 0."""
        q, _ = self._make_queue()
        active = {"dev-1"}
        cleaned = await q.cleanup_orphan_flags(active)
        assert cleaned == 0
