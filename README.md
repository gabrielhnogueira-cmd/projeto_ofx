# Leitor de extrato OFX

Lê o arquivo `extrato.ofx`, exibe as movimentações e grava os registros na tabela
`movimentacoes` de um banco PostgreSQL.

## Instalação e execução

Edite o dicionário `CONFIG_BANCO` no início de `main.py` com os dados do
PostgreSQL. O código está preenchido para `localhost`, porta `5432`, banco
`projeto_ofx` e usuário `postgres`; substitua `SUA_SENHA_AQUI` pela senha local.

```powershell
python -m pip install -r requirements.txt
python main.py
```

Este formato é conveniente para uma atividade local. Não publique nem compartilhe
o arquivo com uma senha real. A tabela `movimentacoes` precisa existir no banco
selecionado. Descrições com mais de 255 caracteres são truncadas para respeitar
o tamanho da coluna.

## Conferência no DBeaver

Conecte ao mesmo banco configurado acima e execute:

```sql
SELECT id, data_movimentacao, valor, descricao
FROM movimentacoes
ORDER BY id;
```

Cada execução do script insere todas as transações do arquivo novamente. Como a
tabela não possuía uma chave de identificação da transação do OFX, o script
adiciona a coluna `ofx_fitid` e um índice único na primeira execução. O FITID
identifica uma transação e execuções repetidas ignoram registros já gravados.
Linhas antigas são associadas ao FITID quando data, valor e descrição coincidem.
O usuário do banco precisa ter permissão para alterar a tabela e criar o índice.

Se uma transação não tiver FITID, o script gera uma chave com base na data,
valor, descrição e posição entre registros idênticos daquele arquivo.