# Uso de IA — preparação do banco neste repositório

O histórico do pipeline PostgreSQL importado está em [histórico de origem](../../database/reproducao/.claude/specs/99_uso_ia.md). Este registro descreve a preparação na pasta `D:\Users\Rayani\Documents\GitHub\dengue_nordeste`.

| Data | Quem | Ferramenta | Etapa | O que foi gerado | Como foi verificado |
|---|---|---|---|---|---|
| 13/11/2026 | Rayani Gomes Bezerra | Codex (GPT-6) | Transferência e backup PostgreSQL | database/estrutura.sql; backup completo local em database/backups; pacote de reprodução, requisitos e decisões; manifestos e catálogo em database/validacao; instruções e ligação no README; proteção de backups e configurações privadas no .gitignore | pg_dump concluído; pg_restore --list e leitura/descompressão integral aprovados; 54 partições anuais com dados conferidas no catálogo, além das tabelas tratadas de public; arquivo final de 3.371.550.780 bytes com SHA-256 registrado; 16 arquivos copiados idênticos à origem por SHA-256 e requisitos específicos; sintaxe Python conferida e exclusão do backup/credenciais do Git verificada. Restauração em outro banco não executada. Serviço e dados de origem preservados. Sem commits ou pushes |
