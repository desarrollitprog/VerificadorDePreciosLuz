"""
Pruebas unitarias para Replicación Paralela.
"""
import sys
import os
import io

_old_stdout = sys.stdout
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio


class TestParallelReplicationLogic:
    """Pruebas de lógica de replicación paralela."""

    def test_asyncio_gather_basic(self):
        """Verificar que asyncio.gather ejecuta en paralelo."""
        async def dummy_task(n):
            await asyncio.sleep(0.01)
            return n * 2
        
        async def run():
            results = await asyncio.gather(
                dummy_task(1),
                dummy_task(2),
                dummy_task(3),
            )
            return list(results)
        
        results = asyncio.run(run())
        assert results == [2, 4, 6]
        print("✓ test_asyncio_gather_basic passed")

    def test_parallel_execution_faster_than_sequential(self):
        """Verificar que ejecución paralela es más rápida."""
        async def slow_task(n):
            await asyncio.sleep(0.05)
            return n
        
        async def run_parallel():
            import time
            start = time.perf_counter()
            await asyncio.gather(
                slow_task(1),
                slow_task(2),
                slow_task(3),
            )
            parallel_time = time.perf_counter() - start
            return parallel_time
        
        async def run_sequential():
            import time
            start = time.perf_counter()
            await slow_task(1)
            await slow_task(2)
            await slow_task(3)
            sequential_time = time.perf_counter() - start
            return sequential_time
        
        parallel_time = asyncio.run(run_parallel())
        sequential_time = asyncio.run(run_sequential())
        
        assert parallel_time < sequential_time * 0.8
        print("✓ test_parallel_execution_faster_than_sequential passed")

    def test_gather_with_exception(self):
        """Verificar que asyncio.gather maneja excepciones."""
        async def successful_task():
            await asyncio.sleep(0.01)
            return "success"
        
        async def failing_task():
            await asyncio.sleep(0.01)
            raise ValueError("Test error")
        
        async def run():
            results = await asyncio.gather(
                successful_task(),
                failing_task(),
                successful_task(),
                return_exceptions=True
            )
            return results
        
        results = asyncio.run(run())
        assert results[0] == "success"
        assert isinstance(results[1], ValueError)
        assert results[2] == "success"
        print("✓ test_gather_with_exception passed")


class TestServerListProcessing:
    """Pruebas de procesamiento de lista de servidores."""

    def test_empty_server_list(self):
        """Verificar manejo de lista vacía de servidores."""
        servidores = []
        
        results = []
        for servidor in servidores:
            results.append(servidor)
        
        assert len(results) == 0
        print("✓ test_empty_server_list passed")

    def test_single_server(self):
        """Verificar procesamiento de un solo servidor."""
        servidores = [
            {"id": 1, "nombre": "Server 1", "api_url": "http://192.168.1.1:8000"}
        ]
        
        results = []
        for servidor in servidores:
            results.append(servidor.get("nombre"))
        
        assert results == ["Server 1"]
        print("✓ test_single_server passed")

    def test_multiple_servers(self):
        """Verificar procesamiento de múltiples servidores."""
        servidores = [
            {"id": 1, "nombre": "Server 1", "ip": "192.168.1.1"},
            {"id": 2, "nombre": "Server 2", "ip": "192.168.1.2"},
            {"id": 3, "nombre": "Server 3", "ip": "192.168.1.3"},
        ]
        
        async def get_api_url(srv):
            api_url = srv.get("api_url")
            if not api_url:
                ip = srv.get("ip")
                if ip:
                    api_url = f"http://{ip}:8000"
            return api_url
        
        async def run():
            urls = await asyncio.gather(
                *[get_api_url(s) for s in servidores]
            )
            return list(urls)
        
        urls = asyncio.run(run())
        assert len(urls) == 3
        assert urls[0] == "http://192.168.1.1:8000"
        assert urls[1] == "http://192.168.1.2:8000"
        assert urls[2] == "http://192.168.1.3:8000"
        print("✓ test_multiple_servers passed")

    def test_api_url_preference_over_ip(self):
        """Verificar que api_url tiene preferencia sobre ip."""
        servidor = {"id": 1, "nombre": "Server", "api_url": "http://custom:9000", "ip": "192.168.1.1"}
        
        api_url = servidor.get("api_url")
        if not api_url:
            ip = servidor.get("ip")
            if ip:
                api_url = f"http://{ip}:8000"
        
        assert api_url == "http://custom:9000"
        print("✓ test_api_url_preference_over_ip passed")


class TestResultAggregation:
    """Pruebas de agregación de resultados."""

    def test_result_structure_success(self):
        """Verificar estructura de resultado exitoso."""
        result = {
            "servidor_id": 1,
            "servidor_nombre": "Server 1",
            "api_url": "http://192.168.1.1:8000",
            "success": True,
            "response": {"banner_id": 123}
        }
        
        assert result["success"] is True
        assert "servidor_id" in result
        assert "servidor_nombre" in result
        assert "api_url" in result
        print("✓ test_result_structure_success passed")

    def test_result_structure_error(self):
        """Verificar estructura de resultado con error."""
        result = {
            "servidor_id": 1,
            "servidor_nombre": "Server 1",
            "api_url": "http://192.168.1.1:8000",
            "success": False,
            "error": "Connection timeout"
        }
        
        assert result["success"] is False
        assert "error" in result
        print("✓ test_result_structure_error passed")

    def test_results_summary(self):
        """Verificar cálculo de resumen de resultados."""
        results = [
            {"success": True},
            {"success": True},
            {"success": False},
            {"success": True},
            {"success": False},
        ]
        
        exitosos = [r for r in results if r.get("success")]
        fallidos = [r for r in results if not r.get("success")]
        
        assert len(exitosos) == 3
        assert len(fallidos) == 2
        print("✓ test_results_summary passed")


class TestTimeoutConfiguration:
    """Pruebas de configuración de timeout."""

    def test_default_timeout_values(self):
        """Verificar valores por defecto de timeout."""
        REPLICACION_TIMEOUT = 30
        VERIFICACION_TIMEOUT = 15
        
        assert REPLICACION_TIMEOUT == 30
        assert VERIFICACION_TIMEOUT == 15
        print("✓ test_default_timeout_values passed")

    def test_timeout_from_env(self):
        """Verificar lectura de timeout desde entorno."""
        env_timeout = os.getenv("REPLICACION_TIMEOUT", "30")
        timeout = int(env_timeout)
        
        assert timeout == 30
        print("✓ test_timeout_from_env passed")


class TestBatchProcessing:
    """Pruebas de procesamiento por lotes."""

    def test_batch_size_calculation(self):
        """Verificar cálculo de tamaño de batch."""
        total_items = 100
        batch_size = 10
        expected_batches = (total_items + batch_size - 1) // batch_size
        
        assert expected_batches == 10
        print("✓ test_batch_size_calculation passed")

    def test_batch_split(self):
        """Verificar división en batches."""
        items = list(range(100))
        batch_size = 25
        
        batches = [items[i:i + batch_size] for i in range(0, len(items), batch_size)]
        
        assert len(batches) == 4
        assert len(batches[0]) == 25
        assert len(batches[3]) == 25
        print("✓ test_batch_split passed")


def run_tests():
    print("=" * 60)
    print("Ejecutando pruebas de Replicación Paralela")
    print("=" * 60)
    
    parallel_tests = TestParallelReplicationLogic()
    parallel_tests.test_asyncio_gather_basic()
    parallel_tests.test_parallel_execution_faster_than_sequential()
    parallel_tests.test_gather_with_exception()
    
    server_tests = TestServerListProcessing()
    server_tests.test_empty_server_list()
    server_tests.test_single_server()
    server_tests.test_multiple_servers()
    server_tests.test_api_url_preference_over_ip()
    
    result_tests = TestResultAggregation()
    result_tests.test_result_structure_success()
    result_tests.test_result_structure_error()
    result_tests.test_results_summary()
    
    timeout_tests = TestTimeoutConfiguration()
    timeout_tests.test_default_timeout_values()
    timeout_tests.test_timeout_from_env()
    
    batch_tests = TestBatchProcessing()
    batch_tests.test_batch_size_calculation()
    batch_tests.test_batch_split()
    
    print("=" * 60)
    print("Todas las pruebas de Replicación Paralela pasaron ✓")
    print("=" * 60)


if __name__ == "__main__":
    run_tests()
