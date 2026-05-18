-- Migration 001: Create subida_log table for immutable banner upload history
-- 
-- This table records every banner creation event.
-- It replaces the previous approach of relying on Publicidad.UpdatedAt,
-- which loses data when banners are deleted.

IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[subida_log]') AND type = 'U')
BEGIN
    CREATE TABLE [dbo].[subida_log] (
        id              INT            IDENTITY(1,1) NOT NULL PRIMARY KEY,
        publicidad_id   INT            NOT NULL,
        titulo          VARCHAR(200)   NULL,
        fecha_subida    DATETIME       NOT NULL DEFAULT GETDATE()
    );

    CREATE INDEX [ix_subida_log_publicidad_id] ON [dbo].[subida_log] ([publicidad_id]);
    CREATE INDEX [ix_subida_log_fecha_subida] ON [dbo].[subida_log] ([fecha_subida] ASC);

    -- Backfill: insert a log row for every existing banner using UpdatedAt as the upload date
    INSERT INTO [dbo].[subida_log] (publicidad_id, titulo, fecha_subida)
    SELECT IdPublicidad, Titulo, UpdatedAt
    FROM [dbo].[Publicidad]
    WHERE UpdatedAt IS NOT NULL
    ORDER BY UpdatedAt ASC;
END
GO
