-- Migración: Crear tabla SubidaLog para el histórico inmutable de subidas
-- Ejecutar en la base de datos DashboardUsuarios

-- ============================================================
-- Limpiar columnas de la implementación anterior (soft delete)
-- Solo si existen (no dio tiempo a deployarse)
-- ============================================================
IF EXISTS (SELECT 1 FROM sys.columns WHERE object_id = OBJECT_ID('Publicidad') AND name = 'FechaEliminacion')
    ALTER TABLE Publicidad DROP COLUMN FechaEliminacion;

IF EXISTS (SELECT 1 FROM sys.columns WHERE object_id = OBJECT_ID('Publicidad') AND name = 'FechaCreacion')
    ALTER TABLE Publicidad DROP COLUMN FechaCreacion;

-- ============================================================
-- Crear tabla de histórico inmutable
-- ============================================================
CREATE TABLE subida_log (
    id INT IDENTITY(1,1) PRIMARY KEY,
    publicidad_id INT NOT NULL,
    titulo NVARCHAR(200) NULL,
    fecha_subida DATETIME NOT NULL DEFAULT GETDATE()
);

-- Índice para la consulta del timeline (filtro por fecha)
CREATE INDEX IX_subida_log_fecha ON subida_log (fecha_subida);

-- ============================================================
-- Backfill: poblar con subidas existentes
-- Usa UpdatedAt como fecha de subida (es lo más cercano disponible)
-- ============================================================
INSERT INTO subida_log (publicidad_id, titulo, fecha_subida)
SELECT IdPublicidad, Titulo, UpdatedAt FROM Publicidad;

-- ============================================================
-- Verificación
-- ============================================================
SELECT COUNT(*) AS total_registros FROM subida_log;
SELECT TOP 10 * FROM subida_log ORDER BY fecha_subida DESC;
