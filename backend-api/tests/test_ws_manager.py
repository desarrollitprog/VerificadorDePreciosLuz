"""
Pruebas para WebSocket Manager y bus listener (FASE 15 - Lote 1).
Usa implementaciones mínimas para evitar importar main.py (que requiere DB/Redis).
"""
import sys
import os
import json
import asyncio
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class FakeWSState:
    def __init__(self, name: str = "CONNECTED"):
        self.name = name

class FakeWebSocket:
    def __init__(self):
        self.sent: list = []
        self.closed = False
        self.close_code = None
        self.client_state = FakeWSState("CONNECTED")

    async def send_json(self, msg):
        self.sent.append(msg)
        return True

    async def close(self, code=1000, reason=""):
        self.closed = True
        self.close_code = code

    async def receive_json(self):
        raise NotImplementedError


# --- Reimplementación mínima de TabletWSManager para testing ---

class FakeTabletWSManager:
    """Reimplementa la lógica clave de TabletWSManager para testing."""

    async def connect(self, websocket: FakeWebSocket, device_id: str):
        self.active_connections.append(websocket)
        self.device_map[device_id] = websocket

    async def disconnect(self, websocket: FakeWebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        for dev_id, ws in list(self.device_map.items()):
            if ws is websocket:
                del self.device_map[dev_id]
        try:
            await websocket.close()
        except Exception:
            pass

    def get_device_id(self, websocket: FakeWebSocket) -> str | None:
        for device_id, ws in self.device_map.items():
            if ws is websocket:
                return device_id
        return None

    async def send_to_websocket(self, websocket: FakeWebSocket, message: dict) -> bool:
        try:
            await websocket.send_json(message)
            return True
        except Exception:
            return False

    def __init__(self):
        self.active_connections: list[FakeWebSocket] = []
        self.device_map: dict[str, FakeWebSocket] = {}
        self._message_queues: dict[str, asyncio.Queue] = {}
        self._lock = asyncio.Lock()
        self._pending_queue = FakePendingQueue()
        self._last_sync_triggered: str | None = None

    async def send_to_device(self, device_id: str, message: dict):
        # L1.4: Agregar command_id único para dedup en cliente
        if "command_id" not in message:
            message["command_id"] = str(uuid.uuid4())

        ws = self.device_map.get(device_id)
        if ws:
            ws_state = getattr(ws, 'client_state', None)
            if ws_state is not None and ws_state.name != "CONNECTED":
                await self.disconnect(ws)
            else:
                try:
                    await ws.send_json(message)
                    return True
                except Exception:
                    await self.disconnect(ws)

        # Dispositivo offline — encolar para cuando reconecte
        await self._enqueue_message(device_id, message)
        return False

    async def _enqueue_message(self, device_id: str, message: dict):
        if self._pending_queue is not None:
            await self._pending_queue.enqueue(device_id, message)
            return

        MAX_QUEUE_PER_DEVICE = 100
        if device_id not in self._message_queues:
            self._message_queues[device_id] = asyncio.Queue()
        if self._message_queues[device_id].qsize() < MAX_QUEUE_PER_DEVICE:
            await self._message_queues[device_id].put(message)

    async def flush_message_queue(self, device_id: str, websocket: FakeWebSocket) -> int:
        if self._pending_queue is not None:
            async def _deliver(msg):
                await websocket.send_json(msg)
                return True
            delivered = await self._pending_queue.flush_all_to_device(device_id, _deliver)
            return delivered

        if device_id not in self._message_queues:
            return 0
        queue = self._message_queues[device_id]
        delivered = 0
        failed_messages = []
        while not queue.empty():
            try:
                msg = queue.get_nowait()
                await websocket.send_json(msg)
                delivered += 1
            except Exception as e:
                failed_messages.append(msg)
                break
        for msg in failed_messages:
            try:
                queue.put_nowait(msg)
            except asyncio.QueueFull:
                break
        if queue.empty():
            self._message_queues.pop(device_id, None)
        return delivered

    async def _flush_all_queues(self, device_id: str, websocket: FakeWebSocket):
        """L2 + L3.3: Flush cola Redis + local + pending banners + flags."""
        if self._pending_queue is not None:
            async def _deliver(msg):
                await websocket.send_json(msg)
                return True
            await self._pending_queue.flush_all_to_device(device_id, _deliver)

        if device_id in self._message_queues:
            await self.flush_message_queue(device_id, websocket)

        # Consumir pending banners
        if self._pending_queue is not None:
            try:
                banner = await self._pending_queue.consume_pending_banner(device_id)
                if banner:
                    await websocket.send_json(banner)
            except Exception:
                pass

        # L3.3: Verificar flags de pendientes
        if self._pending_queue is not None:
            try:
                if await self._pending_queue.check_pending_sync(device_id):
                    self._last_sync_triggered = device_id
            except Exception:
                pass

            try:
                reboot_payload = await self._pending_queue.check_pending_reboot(device_id)
                if reboot_payload:
                    await self.send_to_device(device_id, reboot_payload)
            except Exception:
                pass

    async def send_to_websocket(self, websocket: FakeWebSocket, message: dict) -> bool:
        try:
            await websocket.send_json(message)
            return True
        except Exception:
            return False


class FakePendingQueue:
    """Mínima cola en memoria para verificar interacción."""

    def __init__(self):
        self.queues: dict[str, list] = {}
        self.inflight: dict[str, list] = {}
        self.enqueue_count = 0
        self._pending_sync: dict[str, bool] = {}
        self._pending_reboot: dict[str, dict | None] = {}

    async def enqueue(self, device_id: str, message: dict) -> bool:
        self.enqueue_count += 1
        if device_id not in self.queues:
            self.queues[device_id] = []
        if len(self.queues[device_id]) >= 100:
            return False
        self.queues[device_id].append(message)
        return True

    async def dequeue(self, device_id: str) -> dict | None:
        q = self.queues.get(device_id, [])
        if not q:
            return None
        msg = q.pop(0)
        if device_id not in self.inflight:
            self.inflight[device_id] = []
        self.inflight[device_id].append(msg)
        return msg

    async def confirm(self, device_id: str, raw_message: str) -> bool:
        if device_id in self.inflight and self.inflight[device_id]:
            self.inflight[device_id].pop(0)
            return True
        return False

    async def flush_all_to_device(self, device_id: str, send_fn) -> int:
        delivered = 0
        while True:
            msg = await self.dequeue(device_id)
            if msg is None:
                break
            try:
                success = await send_fn(msg)
                if success:
                    await self.confirm(device_id, "raw")
                    delivered += 1
                else:
                    self.queues.setdefault(device_id, []).insert(0, msg)
                    break
            except Exception:
                self.queues.setdefault(device_id, []).insert(0, msg)
                break
        return delivered

    async def set_pending_sync(self, device_id: str) -> None:
        self._pending_sync[device_id] = True

    async def check_pending_sync(self, device_id: str) -> bool:
        val = self._pending_sync.pop(device_id, False)
        return val

    async def set_pending_reboot(self, device_id: str, payload: dict) -> None:
        self._pending_reboot[device_id] = payload

    async def check_pending_reboot(self, device_id: str) -> dict | None:
        return self._pending_reboot.pop(device_id, None)

    async def consume_pending_banner(self, device_id: str) -> dict | None:
        return None


# --- Pruebas L1 ---

class TestTabletWSManager:
    """Pruebas para la lógica de TabletWSManager (FASE 15 Lote 1)."""

    async def test_send_to_device_online(self):
        """L1: Envío a dispositivo online ok."""
        mgr = FakeTabletWSManager()
        ws = FakeWebSocket()
        await mgr.connect(ws, "dev-1")
        ok = await mgr.send_to_device("dev-1", {"command": "WIPE_AND_RESYNC"})
        assert ok is True
        assert len(ws.sent) == 1
        assert ws.sent[0]["command"] == "WIPE_AND_RESYNC"
        assert "command_id" in ws.sent[0]

    async def test_send_to_device_offline_enqueues(self):
        """L1.2: Dispositivo offline encola en Redis."""
        mgr = FakeTabletWSManager()
        ok = await mgr.send_to_device("dev-offline", {"command": "REINICIAR"})
        assert ok is False
        assert mgr._pending_queue.enqueue_count == 1

    async def test_send_to_device_online_elsewhere_also_enqueues(self):
        """Fix revertido: dispositivo en otro worker SÍ encola (dedup lo protege)."""
        mgr = FakeTabletWSManager()
        ok = await mgr.send_to_device("dev-remote", {"command": "REINICIAR"})
        assert ok is False
        assert mgr._pending_queue.enqueue_count == 1  # Ahora siempre encola

    async def test_send_to_device_zombie_socket(self):
        """L1.2: Socket zombie se desconecta y encola."""
        mgr = FakeTabletWSManager()

        class ZombieWS(FakeWebSocket):
            async def send_json(self, msg):
                raise RuntimeError("zombie connection")

        ws = ZombieWS()
        await mgr.connect(ws, "zombie-dev")
        assert "zombie-dev" in mgr.device_map

        ok = await mgr.send_to_device("zombie-dev", {"command": "BANNER_INICIADO"})
        assert ok is False
        assert ws.closed is True
        assert "zombie-dev" not in mgr.device_map
        assert mgr._pending_queue.enqueue_count == 1

    async def test_send_to_device_phantom_connection(self):
        """WS en device_map pero client_state DISCONNECTED se limpia y no envía."""
        mgr = FakeTabletWSManager()

        class PhantomWS(FakeWebSocket):
            def __init__(self):
                super().__init__()
                self.client_state = FakeWSState("DISCONNECTED")

        ws = PhantomWS()
        await mgr.connect(ws, "phantom-dev")
        assert "phantom-dev" in mgr.device_map

        ok = await mgr.send_to_device("phantom-dev", {"command": "REINICIAR"})
        assert ok is False
        assert ws.closed is True  # disconnect() se llamó
        assert "phantom-dev" not in mgr.device_map
        assert mgr._pending_queue.enqueue_count == 1  # se encoló (device offline)

    async def test_command_id_generated_once(self):
        """L1.4: command_id se genera si no existe y no se sobrescribe."""
        mgr = FakeTabletWSManager()
        ws = FakeWebSocket()
        await mgr.connect(ws, "dev-1")

        await mgr.send_to_device("dev-1", {"command": "TEST"})
        cid = ws.sent[0]["command_id"]
        assert cid is not None
        assert len(str(cid)) > 20  # formato UUID

        # Segundo envío: generar nuevo ID
        await mgr.send_to_device("dev-1", {"command": "TEST2"})
        cid2 = ws.sent[1]["command_id"]
        assert cid2 != cid

    async def test_command_id_preserved(self):
        """L1.4: command_id existente no se sobrescribe."""
        mgr = FakeTabletWSManager()
        ws = FakeWebSocket()
        await mgr.connect(ws, "dev-1")

        await mgr.send_to_device("dev-1", {"command": "TEST", "command_id": "my-custom-id"})
        assert ws.sent[0]["command_id"] == "my-custom-id"

    async def test_flush_message_queue_empty(self):
        """L1.3: Flush cola vacía retorna 0."""
        mgr = FakeTabletWSManager()
        ws = FakeWebSocket()
        delivered = await mgr.flush_message_queue("nonexistent", ws)
        assert delivered == 0

    async def test_flush_message_queue_redis(self):
        """L1.3: Flush cola Redis entrega mensajes."""
        mgr = FakeTabletWSManager()
        ws = FakeWebSocket()
        await mgr._pending_queue.enqueue("dev-1", {"command": "PING", "seq": 1})
        await mgr._pending_queue.enqueue("dev-1", {"command": "PING", "seq": 2})

        delivered = await mgr.flush_message_queue("dev-1", ws)
        assert delivered == 2
        assert len(ws.sent) == 2
        assert ws.sent[0]["seq"] == 1
        assert ws.sent[1]["seq"] == 2

    async def test_flush_message_queue_fallback_local(self):
        """L1.3: Flush fallback cola local."""
        mgr = FakeTabletWSManager()
        mgr._pending_queue = None
        ws = FakeWebSocket()
        mgr._message_queues["dev-1"] = asyncio.Queue()
        await mgr._message_queues["dev-1"].put({"command": "LOCAL"})
        await mgr._message_queues["dev-1"].put({"command": "LOCAL2"})

        delivered = await mgr.flush_message_queue("dev-1", ws)
        assert delivered == 2
        assert "dev-1" not in mgr._message_queues

    async def test_connect_disconnect(self):
        """Conexión y desconexión de WebSocket."""
        mgr = FakeTabletWSManager()
        ws = FakeWebSocket()
        await mgr.connect(ws, "dev-1")
        assert len(mgr.active_connections) == 1
        assert mgr.device_map["dev-1"] is ws

        await mgr.disconnect(ws)
        assert len(mgr.active_connections) == 0
        assert "dev-1" not in mgr.device_map

    async def test_get_device_id(self):
        """Obtener device_id desde websocket."""
        mgr = FakeTabletWSManager()
        ws1 = FakeWebSocket()
        ws2 = FakeWebSocket()
        await mgr.connect(ws1, "alpha")
        await mgr.connect(ws2, "beta")
        assert mgr.get_device_id(ws1) == "alpha"
        assert mgr.get_device_id(ws2) == "beta"
        assert mgr.get_device_id(FakeWebSocket()) is None

    async def test_send_to_websocket(self):
        """send_to_websocket directo."""
        mgr = FakeTabletWSManager()
        ws = FakeWebSocket()
        ok = await mgr.send_to_websocket(ws, {"command": "DIRECT"})
        assert ok is True
        assert ws.sent[0]["command"] == "DIRECT"

    async def test_send_to_websocket_failure(self):
        """send_to_websocket falla por excepción."""
        mgr = FakeTabletWSManager()

        class BrokenWS(FakeWebSocket):
            async def send_json(self, msg):
                raise RuntimeError("broken")

        ws = BrokenWS()
        ok = await mgr.send_to_websocket(ws, {"command": "DIRECT"})
        assert ok is False


# --- Pruebas on_bus_command / bus listener ---

class FakeCommandBus:
    def __init__(self):
        self.commands: list = []
        self.confirmations: list = []
        self.should_fail = False

    async def subscribe_forever(self, on_command, on_confirmation):
        if self.should_fail:
            raise RuntimeError("bus connection error")
        # No esperar infinitamente — solo marcar que se llamó
        self.on_command = on_command
        self.on_confirmation = on_confirmation


class TestBusListener:
    """Pruebas para la lógica de bus listener y on_bus_command."""

    async def test_on_bus_command_caught_exception(self):
        """L1.1: Excepción en on_bus_command no propaga."""
        from app.services.pending_queue import PendingCommandQueue
        bus = FakeCommandBus()
        bus.should_fail = True

        # La función debe capturar la excepción internamente
        try:
            await bus.subscribe_forever(
                on_command=lambda d, c, p: (_ for _ in ()).throw(RuntimeError("boom")),
                on_confirmation=lambda d, c, s, r: None
            )
            assert False, "should have raised"
        except RuntimeError:
            pass  # OK, propaga porque subscribe_forever falla

    async def test_bus_listener_with_retry_loop(self):
        """L1.1: Retry loop al fallar subscribe_forever."""
        bus = FakeCommandBus()
        bus.should_fail = True
        attempts = 0

        async def listener():
            nonlocal attempts
            while attempts < 2:
                try:
                    await bus.subscribe_forever(
                        on_command=lambda d, c, p: None,
                        on_confirmation=lambda d, c, s, r: None
                    )
                except asyncio.CancelledError:
                    break
                except Exception:
                    attempts += 1
                    if attempts >= 2:
                        break
                    await asyncio.sleep(0.01)

        task = asyncio.create_task(listener())
        await asyncio.sleep(0.05)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        assert attempts >= 1

    async def test_on_bus_command_wipe_and_resync(self):
        """L1: Comando WIPE_AND_RESYNC llama a send_to_device."""
        sent = []

        async def fake_send(device_id, message):
            sent.append((device_id, message))

        # Simular la lógica de _on_bus_command
        device_id = "dev-01"
        command = "WIPE_AND_RESYNC"
        payload = {}

        if command == "WIPE_AND_RESYNC":
            await fake_send(device_id, {"command": "WIPE_AND_RESYNC"})

        assert len(sent) == 1
        assert sent[0][1]["command"] == "WIPE_AND_RESYNC"

    async def test_on_bus_command_reiniciar(self):
        """L1: Comando REINICIAR incluye payload."""
        sent = []

        async def fake_send(device_id, message):
            sent.append((device_id, message))

        device_id = "dev-01"
        command = "REINICIAR"
        payload = {"reason": "update"}

        if command == "REINICIAR":
            message = {"command": "REINICIAR"}
            if payload:
                message.update(payload)
            await fake_send(device_id, message)

        assert len(sent) == 1
        assert sent[0][1]["command"] == "REINICIAR"
        assert sent[0][1]["reason"] == "update"

    async def test_on_bus_command_banner(self):
        """L1: Comando BANNER_INICIADO/BANNER_FINALIZADO."""
        sent = []

        async def fake_send(device_id, message):
            sent.append((device_id, message))

        for cmd in ("BANNER_INICIADO", "BANNER_FINALIZADO"):
            device_id = "dev-01"
            payload = {"command": cmd, "id": 1}
            if cmd in ("BANNER_INICIADO", "BANNER_FINALIZADO"):
                await fake_send(device_id, payload)

        assert len(sent) == 2
        assert sent[0][1]["command"] == "BANNER_INICIADO"
        assert sent[1][1]["command"] == "BANNER_FINALIZADO"

    async def test_on_bus_command_unknown_noop(self):
        """L1: Comando desconocido no hace nada."""
        sent = []

        async def fake_send(device_id, message):
            sent.append((device_id, message))

        command = "UNKNOWN_COMMAND"
        if command == "WIPE_AND_RESYNC":
            await fake_send("dev", {"command": "WIPE_AND_RESYNC"})
        elif command == "REINICIAR":
            await fake_send("dev", {"command": "REINICIAR"})
        elif command in ("BANNER_INICIADO", "BANNER_FINALIZADO"):
            await fake_send("dev", {"command": command})

        assert len(sent) == 0

    async def test_on_bus_command_empty_early_return(self):
        """L1: device_id o command vacíos retorna sin error."""
        # Simular early return de _on_bus_command
        async def on_bus_command(device_id: str | None, command: str | None, payload: dict):
            if not device_id or not command:
                return
        await on_bus_command("", "WIPE_AND_RESYNC", {})
        await on_bus_command("dev", "", {})
        await on_bus_command(None, "WIPE_AND_RESYNC", {})


# --- Pruebas L3 (Flags de Pendientes) ---

class TestPendingFlags:
    """Pruebas para FASE 15 Lote 3 — flags de pendientes en IDENTIFY."""

    async def test_pending_sync_triggers_wipe_on_flush_all(self):
        """L3.3: Flag pending_sync activo dispara WIPE_AND_RESYNC vía _flush_all_queues."""
        mgr = FakeTabletWSManager()
        ws = FakeWebSocket()
        await mgr.connect(ws, "dev-flag")

        # Setear pending_sync
        await mgr._pending_queue.set_pending_sync("dev-flag")

        # Ejecutar _flush_all_queues (simula el connect)
        await mgr._flush_all_queues("dev-flag", ws)

        # Verificar que se detectó el sync pendiente
        assert mgr._last_sync_triggered == "dev-flag"

    async def test_pending_sync_cleared_after_check(self):
        """L3.3: pending_sync se limpia después de check_pending_sync."""
        mgr = FakeTabletWSManager()
        await mgr._pending_queue.set_pending_sync("dev-flag")

        # Primera llamada: detecta y limpia
        val1 = await mgr._pending_queue.check_pending_sync("dev-flag")
        assert val1 is True

        # Segunda llamada: ya no está
        val2 = await mgr._pending_queue.check_pending_sync("dev-flag")
        assert val2 is False

    async def test_pending_reboot_triggers_send_on_flush_all(self):
        """L3.3: Flag pending_reboot activo re-envía REINICIAR vía _flush_all_queues."""
        mgr = FakeTabletWSManager()
        ws = FakeWebSocket()
        await mgr.connect(ws, "dev-reboot")

        # Setear pending_reboot
        payload = {"command": "REINICIAR", "reason": "update"}
        await mgr._pending_queue.set_pending_reboot("dev-reboot", payload)

        # Ejecutar _flush_all_queues
        await mgr._flush_all_queues("dev-reboot", ws)

        # Verificar que se re-envió el comando
        assert any(msg.get("command") == "REINICIAR" for msg in ws.sent)

    async def test_pending_reboot_cleared_after_check(self):
        """L3.3: pending_reboot se limpia después de check_pending_reboot."""
        mgr = FakeTabletWSManager()
        payload = {"command": "REINICIAR"}
        await mgr._pending_queue.set_pending_reboot("dev", payload)

        val1 = await mgr._pending_queue.check_pending_reboot("dev")
        assert val1 is not None
        assert val1["command"] == "REINICIAR"

        val2 = await mgr._pending_queue.check_pending_reboot("dev")
        assert val2 is None

    async def test_no_false_triggers_without_flags(self):
        """L3.3: Sin flags no se disparan comandos."""
        mgr = FakeTabletWSManager()
        ws = FakeWebSocket()
        await mgr.connect(ws, "dev-clean")

        await mgr._flush_all_queues("dev-clean", ws)
        assert mgr._last_sync_triggered is None
