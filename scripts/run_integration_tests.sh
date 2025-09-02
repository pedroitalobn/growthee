#!/bin/bash

# Definir cores para output
GREEN="\033[0;32m"
RED="\033[0;31m"
NC="\033[0m" # No Color

# Diretório raiz do projeto
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/.."
cd "$ROOT_DIR"

echo "Executando testes de integração do Firecrawl..."

# Executar os testes unitários
python -m unittest tests/test_firecrawl_integration.py

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Testes de integração concluídos com sucesso!${NC}"
    
    # Perguntar se deseja executar o teste manual
    read -p "Deseja executar o teste manual com uma URL real? (s/n): " run_manual
    
    if [[ $run_manual == "s" || $run_manual == "S" ]]; then
        read -p "Digite a URL para testar: " test_url
        read -p "Usar schema de empresa? (s/n): " use_schema
        
        if [[ $use_schema == "s" || $use_schema == "S" ]]; then
            python scripts/test_firecrawl.py --url "$test_url" --schema schemas/company_schema.json --output results/company_data.json
        else
            python scripts/test_firecrawl.py --url "$test_url" --output results/scrape_result.json
        fi
    fi
else
    echo -e "${RED}✗ Falha nos testes de integração${NC}"
    exit 1
fi

# Criar diretório para resultados se não existir
mkdir -p results

exit 0