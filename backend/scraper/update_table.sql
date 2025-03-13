-- Adicionar a coluna created_at que está faltando
DO $$
BEGIN
    -- Verificar se a coluna created_at já existe
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'roleta_numeros' AND column_name = 'created_at'
    ) THEN
        -- Adicionar a coluna created_at
        ALTER TABLE roleta_numeros
        ADD COLUMN created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();
        
        -- Atualizar valores existentes (copiar de timestamp)
        UPDATE roleta_numeros SET created_at = timestamp WHERE created_at IS NULL;
    ELSE
        -- Informar que a coluna já existe
        RAISE NOTICE 'Coluna created_at já existe na tabela roleta_numeros.';
    END IF;
END $$; 