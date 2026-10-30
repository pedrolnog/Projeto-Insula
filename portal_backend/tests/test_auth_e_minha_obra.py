"""Testes automatizados da Fase 4 + Ponto X: Autenticação JWT e Isolamento Estrito por Obra e Unidade."""
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import gerar_hash_senha
from app.main import app
from app.models.enums import OrigemSincronizacao, PerfilUsuario
from app.models.obra import Obra
from app.models.unidade import Unidade
from app.models.usuario import Usuario, usuarios_obras
from app.services.seed_service import garantir_usuarios_iniciais
from app.services.sync_service import SyncService


@pytest.mark.asyncio
async def test_fluxo_completo_auth_e_isolamento_multi_tenancy_obra_e_unidade(
    db_session: AsyncSession,
):
    # 1. Prepara o banco com sincronização Sienge + Seed de Unidades (Apto 302, 501 e 404)
    await db_session.execute(
        text(
            "TRUNCATE TABLE usuarios_unidades, unidades, usuarios_obras, usuarios, "
            "logs_sincronizacao, fotos_diario, tarefas_diario, diarios_obra, obras, empresas CASCADE"
        )
    )
    await db_session.commit()

    sync_svc = SyncService(db=db_session)
    await sync_svc.sincronizar_tudo(origem=OrigemSincronizacao.MANUAL)
    await garantir_usuarios_iniciais(db_session)

    # Busca as obras sincronizadas (101 e 102)
    obras = (
        await db_session.execute(select(Obra).order_by(Obra.sienge_building_id.asc()))
    ).scalars().all()
    assert len(obras) >= 2
    obra_101, obra_102 = obras[0], obras[1]

    # Busca a unidade do vizinho (Apto 404) na mesma Obra 101
    unidade_vizinho_404 = (
        await db_session.execute(
            select(Unidade).where(
                Unidade.obra_id == obra_101.id,
                Unidade.identificador == "Apto 404 - Torre A",
            )
        )
    ).scalar_one()

    # Cria um condômino vinculado exclusivamente à obra 102
    condomino_b = Usuario(
        cpf="99988877766",
        nome="Maria Oliveira (Condômina Obra 102)",
        email="maria@email.com",
        senha_hash=gerar_hash_senha("senha_maria"),
        perfil=PerfilUsuario.CONDOMINO,
        ativo=True,
    )
    db_session.add(condomino_b)
    await db_session.flush()
    await db_session.execute(
        usuarios_obras.insert().values(usuario_id=condomino_b.id, obra_id=obra_102.id)
    )
    await db_session.commit()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # 2. Tentativa de acesso sem token -> 401
        r_sem_token = await client.get("/api/v1/minha-obra")
        assert r_sem_token.status_code == 401

        # 3. Login do Condômino João (Obra 101, dono do Apto 302 e Apto 501)
        r_login_joao = await client.post(
            "/api/v1/auth/login",
            json={"cpf": "111.222.333-44", "senha": "benedetto123"},
        )
        assert r_login_joao.status_code == 200
        dados_login_joao = r_login_joao.json()
        token_joao = dados_login_joao["access_token"]
        headers_joao = {"Authorization": f"Bearer {token_joao}"}

        # LGPD: Termo de privacidade inicialmente não aceito (None)
        assert dados_login_joao["usuario"]["termo_privacidade_aceito_em"] is None

        # Aceite expresso do termo de privacidade no 1º login
        r_termo = await client.post(
            "/api/v1/auth/aceitar-termo-privacidade",
            headers=headers_joao,
        )
        assert r_termo.status_code == 200
        assert r_termo.json()["termo_privacidade_aceito_em"] is not None

        # Confirma que GET /api/v1/auth/me agora reflete o consentimento registrado
        r_me = await client.get("/api/v1/auth/me", headers=headers_joao)
        assert r_me.status_code == 200
        assert r_me.json()["termo_privacidade_aceito_em"] is not None

        # 4. João consulta GET /api/v1/minha-obra -> vê Obra 101 na fase REFORMAS_UNIDADES
        #    e vê APENAS suas 2 unidades (Apto 302 e Apto 501). Apto 404 NÃO pode aparecer!
        r_obra_joao = await client.get("/api/v1/minha-obra", headers=headers_joao)
        assert r_obra_joao.status_code == 200
        dados_obra = r_obra_joao.json()
        assert dados_obra["id"] == obra_101.id
        assert dados_obra["fase_atual"] == "reformas_unidades"

        identificadores_unidades = [
            u["identificador"] for u in dados_obra["unidades_vinculadas"]
        ]
        assert len(identificadores_unidades) == 2
        assert "Apto 302 - Torre A" in identificadores_unidades
        assert "Apto 501 - Torre A" in identificadores_unidades
        assert "Apto 404 - Torre A" not in identificadores_unidades

        # 5. João acessa os detalhes de sua própria unidade (Apto 302) -> 200 OK com fotos e tarefas da unidade
        id_apto_302 = dados_obra["unidades_vinculadas"][0]["id"]
        r_detalhe_302 = await client.get(
            f"/api/v1/minha-obra/unidades/{id_apto_302}",
            headers=headers_joao,
        )
        assert r_detalhe_302.status_code == 200
        dados_302 = r_detalhe_302.json()
        assert dados_302["identificador"] == "Apto 302 - Torre A"
        assert len(dados_302["fotos"]) >= 2
        assert len(dados_302["tarefas"]) >= 2
        assert all(f["unidade_id"] == id_apto_302 for f in dados_302["fotos"])

        # 6. ISOLAMENTO ESTRITO ENTRE UNIDADES DA MESMA OBRA:
        #    João tenta acessar diretamente o Apto 404 do seu vizinho Carlos -> 403 Forbidden!
        r_proibido_404 = await client.get(
            f"/api/v1/minha-obra/unidades/{unidade_vizinho_404.id}",
            headers=headers_joao,
        )
        assert r_proibido_404.status_code == 403

        # 7. ISOLAMENTO NA VISÃO GERAL DO EDIFÍCIO (`/minha-obra/diarios`):
        #    Nenhuma foto ou tarefa que possua `unidade_id != None` (nem do Apto 404, nem do 302)
        #    pode vazar nos diários coletivos do edifício!
        r_diarios_gerais = await client.get(
            "/api/v1/minha-obra/diarios",
            headers=headers_joao,
        )
        assert r_diarios_gerais.status_code == 200
        feed_geral = r_diarios_gerais.json()
        assert len(feed_geral["itens"]) > 0
        for diario in feed_geral["itens"]:
            for foto in diario["fotos"]:
                assert foto["unidade_id"] is None
                assert "Apto 404" not in (foto["descricao"] or "")
            for tarefa in diario["tarefas"]:
                assert tarefa["unidade_id"] is None
                assert "Apto 404" not in (tarefa["descricao"] or "")

        # 8. Isolamento entre Obras: João tenta acessar Obra 102 da Maria -> 403 Forbidden
        r_proibido_obra = await client.get(
            f"/api/v1/minha-obra?obra_id={obra_102.id}",
            headers=headers_joao,
        )
        assert r_proibido_obra.status_code == 403

        # 9. QUARENTENA & CURADORIA ADMIN (Política de Inversão de Risco no Ponto X):
        #    A foto enviada sem tag ("Interior de Apartamento (Sem Tag)") NÃO pode aparecer para João!
        for diario in feed_geral["itens"]:
            for foto in diario["fotos"]:
                assert "Sem Tag" not in (foto["local"] or "")

        # Condômino comum não pode acessar a rota de curadoria -> 403 Forbidden
        r_quarentena_proibido = await client.get(
            "/api/v1/admin/fotos-quarentena",
            headers=headers_joao,
        )
        assert r_quarentena_proibido.status_code == 403

        # Admin faz login e lista as fotos retidas em quarentena
        r_login_admin = await client.post(
            "/api/v1/auth/login",
            json={"cpf": "000.000.000-00", "senha": "admin123"},
        )
        assert r_login_admin.status_code == 200
        headers_admin = {"Authorization": f"Bearer {r_login_admin.json()['access_token']}"}

        r_quarentena = await client.get(
            f"/api/v1/admin/fotos-quarentena?obra_id={obra_101.id}",
            headers=headers_admin,
        )
        assert r_quarentena.status_code == 200
        fotos_retidas = r_quarentena.json()
        assert len(fotos_retidas) >= 1
        foto_sem_tag = fotos_retidas[0]
        assert foto_sem_tag["publicado"] is False
        assert foto_sem_tag["unidade_id"] is None

        # Admin classifica a foto em quarentena atribuindo-a ao Apto 302 com 1 clique
        r_classificar = await client.patch(
            f"/api/v1/admin/fotos/{foto_sem_tag['id']}/classificar",
            headers=headers_admin,
            json={"unidade_id": id_apto_302, "publicado": True},
        )
        assert r_classificar.status_code == 200
        assert r_classificar.json()["unidade_id"] == id_apto_302
        assert r_classificar.json()["publicado"] is True

        # Agora a foto aparece exclusivamente dentro do Apto 302 do João (e continua invisível no feed geral)
        r_detalhe_302_pos = await client.get(
            f"/api/v1/minha-obra/unidades/{id_apto_302}",
            headers=headers_joao,
        )
        ids_fotos_302 = [f["id"] for f in r_detalhe_302_pos.json()["fotos"]]
        assert foto_sem_tag["id"] in ids_fotos_302

        # 10. Admin atualiza o percentual de evolução física geral e a fase da obra
        r_atualizar_obra = await client.patch(
            f"/api/v1/admin/obras/{obra_101.id}",
            headers=headers_admin,
            json={"percentual_concluido": 35.50, "fase_atual": "reformas_unidades"},
        )
        assert r_atualizar_obra.status_code == 200
        dados_atualizados = r_atualizar_obra.json()
        assert dados_atualizados["percentual_concluido"] == 35.50
        assert dados_atualizados["fase_atual"] == "reformas_unidades"

        # Condômino consulta a obra e vê a evolução física geral atualizada instantaneamente
        r_obra_joao_atualizada = await client.get("/api/v1/minha-obra", headers=headers_joao)
        assert r_obra_joao_atualizada.status_code == 200
        assert float(r_obra_joao_atualizada.json()["percentual_concluido"]) == 35.50

        # Tentativa de definir percentual inválido (> 100) -> 422
        r_invalido = await client.patch(
            f"/api/v1/admin/obras/{obra_101.id}",
            headers=headers_admin,
            json={"percentual_concluido": 125.0},
        )
        assert r_invalido.status_code == 422

        # Condômino comum tentando alterar obra -> 403 Forbidden
        r_bloqueado = await client.patch(
            f"/api/v1/admin/obras/{obra_101.id}",
            headers=headers_joao,
            json={"percentual_concluido": 50.0},
        )
        assert r_bloqueado.status_code == 403
