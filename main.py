import hashlib

import psycopg2
from ofxparse import OfxParser

CONFIG_BANCO = {
    "host": "localhost",
    "port": 5432,
    "dbname": "projeto_ofx",
    "user": "postgres",
    "password": "SUA_SENHA_AQUI",
    "client_encoding": "UTF8",
}

with open("extrato.ofx", "rb") as arquivo:
    ofx = OfxParser.parse(arquivo)

print("EXTRATO BANCÁRIO")

movimentacoes = ofx.account.statement.transactions

for t in movimentacoes:

    print(f"""
Data      : {t.date.strftime('%d/%m/%Y')}
Valor     : R$ {t.amount:.2f}
Descrição : {t.memo}
--------------------------------------
""")

total_entradas = sum(t.amount for t in movimentacoes if t.amount > 0)
total_saidas = sum(abs(t.amount) for t in movimentacoes if t.amount < 0)
saldo = total_entradas - total_saidas

print(f"Quantidade total de movimentações encontradas: {len(movimentacoes)}")
print(f"Total de entradas: R$ {total_entradas:.2f}")
print(f"Total de saídas: R$ {total_saidas:.2f}")
print(f"Saldo calculado: R$ {saldo:.2f}")

dados_movimentacoes = []
ocorrencias_sem_fitid = {}

for t in movimentacoes:
    data = t.date.date()
    valor = t.amount
    descricao = (t.memo or "")[:255]
    fitid = str(t.id or "").strip()

    if not fitid:
        chave = (data, valor, descricao)
        ocorrencia = ocorrencias_sem_fitid.get(chave, 0)
        ocorrencias_sem_fitid[chave] = ocorrencia + 1
        conteudo = f"{data.isoformat()}|{valor}|{descricao}|{ocorrencia}"
        fitid = f"fallback:{hashlib.sha256(conteudo.encode('utf-8')).hexdigest()}"

    dados_movimentacoes.append((fitid, data, valor, descricao))

with psycopg2.connect(**CONFIG_BANCO) as conexao:
    with conexao.cursor() as cursor:
        cursor.execute(
            "ALTER TABLE movimentacoes ADD COLUMN IF NOT EXISTS ofx_fitid VARCHAR(255)"
        )
        cursor.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS uq_movimentacoes_ofx_fitid
            ON movimentacoes (ofx_fitid)
            """
        )
        cursor.execute(
            """
            SELECT id, data_movimentacao, valor, descricao, ofx_fitid
            FROM movimentacoes
            """
        )

        fitids_existentes = set()
        registros_legados = {}

        for registro_id, data, valor, descricao, fitid in cursor.fetchall():
            if fitid:
                fitids_existentes.add(fitid)
            else:
                chave = (data, valor, descricao)
                registros_legados.setdefault(chave, []).append(registro_id)

        inseridas = 0
        duplicadas = 0

        for fitid, data, valor, descricao in dados_movimentacoes:
            if fitid in fitids_existentes:
                duplicadas += 1
                continue

            chave = (data, valor, descricao)
            ids_legados = registros_legados.get(chave, [])

            if ids_legados:
                registro_id = ids_legados.pop()
                cursor.execute(
                    "UPDATE movimentacoes SET ofx_fitid = %s WHERE id = %s",
                    (fitid, registro_id),
                )
                fitids_existentes.add(fitid)
                duplicadas += 1
                continue

            cursor.execute(
                """
                INSERT INTO movimentacoes
                    (ofx_fitid, data_movimentacao, valor, descricao)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (ofx_fitid) DO NOTHING
                """,
                (fitid, data, valor, descricao),
            )

            if cursor.rowcount:
                fitids_existentes.add(fitid)
                inseridas += 1
            else:
                duplicadas += 1

print(f"Movimentações gravadas no PostgreSQL: {inseridas}")
print(f"Movimentações duplicadas ignoradas: {duplicadas}")