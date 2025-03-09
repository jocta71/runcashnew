-- Script para criar a tabela roleta_numeros e funcionalidades associadas

-- Criar a tabela principal
CREATE TABLE IF NOT EXISTS roleta_numeros (
    id SERIAL PRIMARY KEY,
    roleta_id TEXT NOT NULL,
    roleta_nome TEXT NOT NULL,
    numero INTEGER NOT NULL CHECK (numero >= 0 AND numero <= 36),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Índices para melhorar a performance das consultas
CREATE INDEX IF NOT EXISTS idx_roleta_numeros_roleta_id ON roleta_numeros(roleta_id);
CREATE INDEX IF NOT EXISTS idx_roleta_numeros_numero ON roleta_numeros(numero);
CREATE INDEX IF NOT EXISTS idx_roleta_numeros_created_at ON roleta_numeros(created_at);

-- Comentários para documentação
COMMENT ON TABLE roleta_numeros IS 'Tabela para armazenar números individuais de roletas';
COMMENT ON COLUMN roleta_numeros.id IS 'Identificador único do registro';
COMMENT ON COLUMN roleta_numeros.roleta_id IS 'ID da roleta';
COMMENT ON COLUMN roleta_numeros.roleta_nome IS 'Nome da roleta';
COMMENT ON COLUMN roleta_numeros.numero IS 'Número sorteado (0-36)';
COMMENT ON COLUMN roleta_numeros.created_at IS 'Data e hora em que o número foi registrado';

-- Função para limitar o número de registros por roleta (máximo 1000)
CREATE OR REPLACE FUNCTION limit_roleta_numeros() RETURNS TRIGGER AS $$
DECLARE
    registros_excedentes INTEGER;
    limite_registros INTEGER := 1000;
BEGIN
    -- Verificar quantos registros existem para esta roleta
    SELECT COUNT(*) INTO registros_excedentes
    FROM roleta_numeros
    WHERE roleta_id = NEW.roleta_id;
    
    -- Se tiver mais de 1000 registros, excluir os mais antigos
    IF registros_excedentes > limite_registros THEN
        DELETE FROM roleta_numeros
        WHERE id IN (
            SELECT id
            FROM roleta_numeros
            WHERE roleta_id = NEW.roleta_id
            ORDER BY created_at ASC
            LIMIT (registros_excedentes - limite_registros)
        );
    END IF;
    
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Trigger para executar a função após cada inserção
CREATE TRIGGER trigger_limit_roleta_numeros
AFTER INSERT ON roleta_numeros
FOR EACH ROW
EXECUTE FUNCTION limit_roleta_numeros();

-- View para facilitar consultas comuns
CREATE OR REPLACE VIEW vw_ultimos_numeros_roleta AS
SELECT 
    roleta_id,
    roleta_nome,
    numero,
    created_at,
    ROW_NUMBER() OVER (PARTITION BY roleta_id ORDER BY created_at DESC) as ordem
FROM 
    roleta_numeros;

-- Função para obter os últimos N números de uma roleta
CREATE OR REPLACE FUNCTION get_ultimos_numeros(p_roleta_id TEXT, p_limite INTEGER DEFAULT 100)
RETURNS TABLE (numero INTEGER, created_at TIMESTAMPTZ) AS $$
BEGIN
    RETURN QUERY
    SELECT rn.numero, rn.created_at
    FROM roleta_numeros rn
    WHERE rn.roleta_id = p_roleta_id
    ORDER BY rn.created_at DESC
    LIMIT p_limite;
END;
$$ LANGUAGE plpgsql; 