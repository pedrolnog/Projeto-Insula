"""Utilitário CLI completo para gerenciar perfis de usuários e obras — Portal do Condômino Benedetto.

Exemplos de uso rápido no terminal:
  1. Listar todos os perfis cadastrados:
     python scripts/criar_usuario.py --listar

  2. Listar todas as obras e seus IDs no banco:
     python scripts/criar_usuario.py --listar-obras

  3. Visualizar um perfil específico (por CPF ou ID):
     python scripts/criar_usuario.py --ver 09135315458

  4. Criar um Condômino vinculado a UMA ou MÚLTIPLAS obras (IDs separados por espaço):
     python scripts/criar_usuario.py --cpf 12345678900 --nome "Ana Condômina" --senha "benedetto123" --perfil condomino --obras 128 129

  5. Adicionar obras a um condômino sem apagar as que ele já tem:
     python scripts/criar_usuario.py --cpf 12345678900 --adicionar-obras 130 131

  6. Remover obras específicas de um condômino:
     python scripts/criar_usuario.py --cpf 12345678900 --remover-obras 129

  7. Criar (ou atualizar) um Administrador (Admins enxergam todas as obras automaticamente):
     python scripts/criar_usuario.py --cpf 09135315458 --nome "Pedro Lucas" --senha "sua_senha" --perfil admin

  8. Apagar um perfil (por CPF ou ID):
     python scripts/criar_usuario.py --apagar 12345678900

  9. Limpar dados Mock residuais (Obras 101/102 e CPFs 00000000000, 11122233344):
     python scripts/criar_usuario.py --limpar-mocks

  10. Menu Interativo completo:
      python scripts/criar_usuario.py
"""
import argparse
import asyncio
import sys

# Garante compatibilidade de saída UTF-8 com terminais Windows PowerShell / CMD
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from decimal import Decimal

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.database import AsyncSessionLocal
from app.core.security import gerar_hash_senha_async, normalizar_cpf
from app.models.enums import FaseObra, PerfilUsuario
from app.models.obra import Obra
from app.models.unidade import Unidade, usuarios_unidades
from app.models.usuario import Usuario, usuarios_obras


async def _resolver_usuario(db, identificador: str) -> Usuario | None:
    ident_limpo = normalizar_cpf(identificador)
    if len(ident_limpo) == 11:
        stmt = select(Usuario).where(Usuario.cpf == ident_limpo)
        u = (await db.execute(stmt)).scalar_one_or_none()
        if u:
            return u
    if identificador.strip().isdigit():
        stmt_id = select(Usuario).where(Usuario.id == int(identificador.strip()))
        return (await db.execute(stmt_id)).scalar_one_or_none()
    return None


async def listar_obras_cmd() -> None:
    async with AsyncSessionLocal() as db:
        obras = list(
            (await db.execute(select(Obra).order_by(Obra.id.asc()))).scalars().all()
        )
        if not obras:
            print("[AVISO] Nenhuma obra cadastrada no banco.")
            return

        print("\n" + "=" * 110)
        print(
            f"{'ID':<6} | {'SIENGE ID':<10} | {'NOME DA OBRA':<36} | {'CIDADE/UF':<18} | {'FASE':<18} | {'% CONCLUÍDO'}"
        )
        print("-" * 110)
        for o in obras:
            cid_uf = f"{o.cidade or '-'}/{o.uf or '-'}"
            pct = (
                f"{float(o.percentual_concluido):.2f}%"
                if o.percentual_concluido is not None
                else "0.00%"
            )
            fase = o.fase_atual.value if hasattr(o.fase_atual, "value") else str(o.fase_atual)
            print(
                f"{o.id:<6} | {o.sienge_building_id!s:<10} | {o.nome[:36]:<36} | "
                f"{cid_uf[:18]:<18} | {fase[:18]:<18} | {pct}"
            )
        print("=" * 110 + f"\nTotal: {len(obras)} obra(s) cadastrada(s).\n")


async def listar_usuarios_cmd() -> None:
    async with AsyncSessionLocal() as db:
        usuarios = list(
            (await db.execute(select(Usuario).order_by(Usuario.id.asc()))).scalars().all()
        )
        if not usuarios:
            print("[AVISO] Nenhum usuário cadastrado no banco.")
            return

        ids_u = [u.id for u in usuarios]
        obras_map: dict[int, list[int]] = {uid: [] for uid in ids_u}
        unids_map: dict[int, list[int]] = {uid: [] for uid in ids_u}

        for u_id, o_id in (
            await db.execute(
                select(usuarios_obras.c.usuario_id, usuarios_obras.c.obra_id).where(
                    usuarios_obras.c.usuario_id.in_(ids_u)
                )
            )
        ).all():
            obras_map[u_id].append(o_id)

        for u_id, un_id in (
            await db.execute(
                select(usuarios_unidades.c.usuario_id, usuarios_unidades.c.unidade_id).where(
                    usuarios_unidades.c.usuario_id.in_(ids_u)
                )
            )
        ).all():
            unids_map[u_id].append(un_id)

        print("\n" + "=" * 95)
        print(
            f"{'ID':<5} | {'CPF':<12} | {'PERFIL':<10} | {'ATIVO':<6} | {'NOME':<32} | {'OBRAS':<10} | {'UNIDADES'}"
        )
        print("-" * 95)
        for u in usuarios:
            status_str = "SIM" if u.ativo else "NAO"
            print(
                f"{u.id:<5} | {u.cpf:<12} | {u.perfil.value:<10} | {status_str:<6} | "
                f"{u.nome[:32]:<32} | {obras_map[u.id]!s:<10} | {unids_map[u.id]}"
            )
        print("=" * 95 + f"\nTotal: {len(usuarios)} perfil(is) cadastrado(s).")
        print("💡 Dica: Use 'python scripts/criar_usuario.py --listar-obras' para ver todos os IDs de obras.\n")


async def ver_usuario_cmd(identificador: str) -> None:
    async with AsyncSessionLocal() as db:
        u = await _resolver_usuario(db, identificador)
        if not u:
            print(f"[ERRO] Usuário '{identificador}' não encontrado (informe o CPF de 11 dígitos ou ID).")
            sys.exit(1)

        obras = (
            await db.execute(
                select(Obra.id, Obra.nome)
                .join(usuarios_obras, usuarios_obras.c.obra_id == Obra.id)
                .where(usuarios_obras.c.usuario_id == u.id)
            )
        ).all()
        unidades = (
            await db.execute(
                select(Unidade.id, Unidade.identificador)
                .join(usuarios_unidades, usuarios_unidades.c.unidade_id == Unidade.id)
                .where(usuarios_unidades.c.usuario_id == u.id)
            )
        ).all()

        print("\n=== DETALHES DO PERFIL ===")
        print(f"  ID:           {u.id}")
        print(f"  CPF:          {u.cpf}")
        print(f"  Nome:         {u.nome}")
        print(f"  Perfil:       {u.perfil.value.upper()}")
        print(f"  Ativo:        {'Sim' if u.ativo else 'Não'}")
        print(f"  E-mail:       {u.email or '-'}")
        print(f"  Telefone:     {u.telefone or '-'}")
        print(f"  Último Login: {u.ultimo_login_em or 'Nunca acessou'}")
        if u.perfil == PerfilUsuario.ADMIN:
            print("  Obras:        [ADMIN ACESSA 100% DAS OBRAS AUTOMATICAMENTE]")
        else:
            print(f"  Obras:        {[f'{oid}: {onome}' for oid, onome in obras] or 'Nenhuma'}")
        print(f"  Unidades:     {[f'{uid}: {uident}' for uid, uident in unidades] or 'Nenhuma'}\n")


async def criar_ou_atualizar_usuario_cmd(
    cpf: str,
    nome: str | None = None,
    senha: str | None = None,
    perfil: str | None = None,
    email: str | None = None,
    telefone: str | None = None,
    ativo: bool | None = None,
    obras_ids: list[int] | None = None,
    adicionar_obras_ids: list[int] | None = None,
    remover_obras_ids: list[int] | None = None,
    unidades_ids: list[int] | None = None,
) -> None:
    cpf_limpo = normalizar_cpf(cpf)
    if len(cpf_limpo) != 11:
        print(f"[ERRO] CPF inválido ({cpf}). Deve conter exatamente 11 dígitos numéricos.")
        sys.exit(1)

    async with AsyncSessionLocal() as db:
        stmt_existente = select(Usuario).where(Usuario.cpf == cpf_limpo)
        usuario = (await db.execute(stmt_existente)).scalar_one_or_none()

        if usuario:
            print(f"[INFO] Atualizando perfil existente ID={usuario.id} (CPF={cpf_limpo})...")
            if nome:
                usuario.nome = nome.strip()
            if senha:
                usuario.senha_hash = await gerar_hash_senha_async(senha)
            if perfil:
                usuario.perfil = (
                    PerfilUsuario.ADMIN if perfil.lower() == "admin" else PerfilUsuario.CONDOMINO
                )
            if email is not None:
                usuario.email = email.strip() or None
            if telefone is not None:
                usuario.telefone = telefone.strip() or None
            if ativo is not None:
                usuario.ativo = ativo
        else:
            if not senha:
                senha = "benedetto123"
            perfil_enum = (
                PerfilUsuario.ADMIN
                if (perfil or "").lower() == "admin"
                else PerfilUsuario.CONDOMINO
            )
            usuario = Usuario(
                cpf=cpf_limpo,
                nome=(nome or "Novo Usuário").strip(),
                email=email.strip() if email else None,
                telefone=telefone.strip() if telefone else None,
                senha_hash=await gerar_hash_senha_async(senha),
                perfil=perfil_enum,
                ativo=True if ativo is None else ativo,
            )
            db.add(usuario)
            await db.flush()
            print(f"[OK] Novo perfil criado com sucesso! ID={usuario.id}")

        # Se for condômino novo sem nenhuma obra informada, vincula à obra principal ativa
        if (
            obras_ids is None
            and adicionar_obras_ids is None
            and usuario.perfil == PerfilUsuario.CONDOMINO
        ):
            qtd_obras_atuais = (
                await db.execute(
                    select(func.count())
                    .select_from(usuarios_obras)
                    .where(usuarios_obras.c.usuario_id == usuario.id)
                )
            ).scalar_one()
            if qtd_obras_atuais == 0:
                obra_principal = (
                    await db.execute(
                        select(Obra).where(Obra.visivel_portal.is_(True)).order_by(Obra.id.asc()).limit(1)
                    )
                ).scalar_one_or_none()
                if obra_principal:
                    obras_ids = [obra_principal.id]

        # 1. Substituir todas as obras vinculadas (caso --obras tenha sido passado)
        if obras_ids is not None:
            await db.execute(
                delete(usuarios_obras).where(usuarios_obras.c.usuario_id == usuario.id)
            )
            for oid in obras_ids:
                obra = (await db.execute(select(Obra).where(Obra.id == oid))).scalar_one_or_none()
                if obra:
                    await db.execute(
                        pg_insert(usuarios_obras)
                        .values(usuario_id=usuario.id, obra_id=oid)
                        .on_conflict_do_nothing(index_elements=["usuario_id", "obra_id"])
                    )
                    print(f"   -> Vinculado à Obra ID={oid} ({obra.nome})")
                else:
                    print(f"   [AVISO] Obra ID={oid} não encontrada no banco.")

        # 2. Adicionar novas obras (sem desvincular as existentes)
        if adicionar_obras_ids:
            for oid in adicionar_obras_ids:
                obra = (await db.execute(select(Obra).where(Obra.id == oid))).scalar_one_or_none()
                if obra:
                    await db.execute(
                        pg_insert(usuarios_obras)
                        .values(usuario_id=usuario.id, obra_id=oid)
                        .on_conflict_do_nothing(index_elements=["usuario_id", "obra_id"])
                    )
                    print(f"   -> Adicionada vinculação com a Obra ID={oid} ({obra.nome})")
                else:
                    print(f"   [AVISO] Obra ID={oid} não encontrada no banco.")

        # 3. Remover obras específicas
        if remover_obras_ids:
            for oid in remover_obras_ids:
                await db.execute(
                    delete(usuarios_obras).where(
                        usuarios_obras.c.usuario_id == usuario.id,
                        usuarios_obras.c.obra_id == oid,
                    )
                )
                print(f"   -> Desvinculado da Obra ID={oid}")

        # Atualiza vínculos de Unidades se fornecidos
        if unidades_ids is not None:
            await db.execute(
                delete(usuarios_unidades).where(usuarios_unidades.c.usuario_id == usuario.id)
            )
            for uid in unidades_ids:
                unid = (
                    await db.execute(select(Unidade).where(Unidade.id == uid))
                ).scalar_one_or_none()
                if unid:
                    await db.execute(
                        pg_insert(usuarios_unidades)
                        .values(usuario_id=usuario.id, unidade_id=uid)
                        .on_conflict_do_nothing(index_elements=["usuario_id", "unidade_id"])
                    )
                    print(f"   -> Vinculado à Unidade ID={uid} ({unid.identificador})")
                else:
                    print(f"   [AVISO] Unidade ID={uid} não encontrada no banco.")

        await db.commit()
        print("\n[SUCESSO] Operação concluída com sucesso!")
        print(f"   * ID:     {usuario.id}")
        print(f"   * CPF:    {usuario.cpf}")
        print(f"   * Nome:   {usuario.nome}")
        print(f"   * Perfil: {usuario.perfil.value.upper()}")
        print(f"   * Ativo:  {'SIM' if usuario.ativo else 'NÃO'}")


async def apagar_usuario_cmd(identificador: str) -> None:
    async with AsyncSessionLocal() as db:
        u = await _resolver_usuario(db, identificador)
        if not u:
            print(f"[ERRO] Usuário '{identificador}' não encontrado.")
            sys.exit(1)

        if u.perfil == PerfilUsuario.ADMIN:
            qtd_admins = (
                await db.execute(
                    select(func.count())
                    .select_from(Usuario)
                    .where(Usuario.perfil == PerfilUsuario.ADMIN, Usuario.ativo.is_(True))
                )
            ).scalar_one()
            if qtd_admins <= 1:
                print("[ERRO] Operação bloqueada: não é permitido apagar o único administrador ativo do sistema.")
                sys.exit(1)

        nome_removido = u.nome
        cpf_removido = u.cpf
        id_removido = u.id
        await db.delete(u)
        await db.commit()
        print(f"[SUCESSO] Perfil removido permanentemente: ID={id_removido} | CPF={cpf_removido} | Nome={nome_removido}")


async def limpar_mocks_cmd() -> None:
    async with AsyncSessionLocal() as db:
        cpfs_mock = ["00000000000", "11122233344", "22233344455"]
        res_u = await db.execute(delete(Usuario).where(Usuario.cpf.in_(cpfs_mock)))
        res_o = await db.execute(delete(Obra).where(Obra.sienge_building_id.in_([101, 102])))
        await db.commit()
        print(f"[SUCESSO] Limpeza de mocks concluída: {res_u.rowcount} usuário(s) e {res_o.rowcount} obra(s) mock removidos.")


async def definir_obra_cmd(
    obra_id: int,
    percentual: float | None = None,
    fase: str | None = None,
    situacao: str | None = None,
) -> None:
    async with AsyncSessionLocal() as db:
        obra = (await db.execute(select(Obra).where(Obra.id == obra_id))).scalar_one_or_none()
        if not obra:
            print(f"[ERRO] Obra com ID {obra_id} não encontrada. Use --listar-obras para ver os IDs.")
            sys.exit(1)

        if percentual is not None:
            if percentual < 0 or percentual > 100:
                print(f"[ERRO] Percentual inválido: {percentual}%. Deve estar entre 0.00% e 100.00%.")
                sys.exit(1)
            obra.percentual_concluido = Decimal(f"{percentual:.2f}")

        if fase is not None:
            try:
                obra.fase_atual = FaseObra(fase)
            except ValueError:
                print(f"[ERRO] Fase inválida '{fase}'. Opções permitidas: estrutural_geral, reformas_unidades, entrega")
                sys.exit(1)

        if situacao is not None:
            obra.situacao = situacao

        await db.commit()
        await db.refresh(obra)
        print(f"\n[SUCESSO] Obra ID={obra.id} ({obra.nome}) atualizada:")
        print(f"   * Evolução Física Geral: {obra.percentual_concluido}%")
        print(f"   * Fase Atual:            {obra.fase_atual.value}")
        if obra.situacao:
            print(f"   * Situação:              {obra.situacao}")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Gerenciador de Perfis de Usuários e Obras — Portal do Condômino Benedetto"
    )
    parser.add_argument("--listar", action="store_true", help="Lista todos os perfis cadastrados")
    parser.add_argument("--listar-obras", action="store_true", help="Lista todas as obras disponíveis e seus IDs")
    parser.add_argument("--ver", metavar="CPF_OU_ID", help="Exibe os detalhes completos de um perfil")
    parser.add_argument("--apagar", metavar="CPF_OU_ID", help="Remove permanentemente um perfil por CPF ou ID")
    parser.add_argument("--limpar-mocks", action="store_true", help="Remove usuários e obras mock residuais")
    parser.add_argument("--cpf", help="CPF com ou sem pontuação para criar ou atualizar um perfil")
    parser.add_argument("--nome", help="Nome completo do usuário")
    parser.add_argument("--senha", help="Senha de acesso (mínimo 6 caracteres)")
    parser.add_argument("--perfil", choices=["admin", "condomino"], help="Perfil de permissão")
    parser.add_argument("--email", help="E-mail (opcional)")
    parser.add_argument("--telefone", help="Telefone (opcional)")
    parser.add_argument("--ativo", choices=["true", "false"], help="Ativa ou desativa o perfil")
    parser.add_argument(
        "--obras",
        nargs="*",
        type=int,
        help="Substitui a lista de obras vinculadas (ex: --obras 128 129 130)",
    )
    parser.add_argument(
        "--adicionar-obras",
        nargs="*",
        type=int,
        help="Adiciona obras à lista existente do condômino sem remover as atuais",
    )
    parser.add_argument(
        "--remover-obras",
        nargs="*",
        type=int,
        help="Remove obras específicas da lista do condômino",
    )
    parser.add_argument(
        "--unidades",
        nargs="*",
        type=int,
        help="Lista de IDs de unidades vinculadas",
    )
    parser.add_argument(
        "--definir-obra-percentual",
        nargs=2,
        metavar=("OBRA_ID", "PERCENTUAL"),
        help="Define o percentual de evolução física geral de uma obra (ex: --definir-obra-percentual 128 15.5)",
    )
    parser.add_argument(
        "--definir-obra-fase",
        nargs=2,
        metavar=("OBRA_ID", "FASE"),
        help="Define a fase da obra (ex: --definir-obra-fase 128 reformas_unidades)",
    )
    return parser.parse_args()


async def menu_interativo() -> None:
    print("\n=== GERENCIADOR DE PERFIS & OBRAS BENEDETTO ===")
    print("  1. Listar todos os perfis de usuários")
    print("  2. Visualizar detalhes de um perfil (CPF ou ID)")
    print("  3. Criar ou Atualizar um perfil (com seletor de obras)")
    print("  4. Apagar um perfil")
    print("  5. Listar todas as Obras disponíveis (IDs e Nomes)")
    print("  6. Limpar dados Mock residuais (Obras 101/102 e Contas Demo)")
    print("  7. Ajustar % de Evolução Física Geral ou Fase de uma Obra")
    opcao = input("\nEscolha uma opção (1-7): ").strip()

    if opcao == "1":
        await listar_usuarios_cmd()
    elif opcao == "2":
        ident = input("Informe o CPF ou ID do perfil: ").strip()
        await ver_usuario_cmd(ident)
    elif opcao == "3":
        cpf = input("CPF (11 dígitos, com ou sem máscara): ").strip()
        nome = input("Nome Completo (deixe em branco p/ manter se já existir): ").strip() or None
        senha = input("Senha de acesso (deixe em branco p/ manter): ").strip() or None
        perfil = input("Perfil (admin/condomino) [padrão: condomino]: ").strip() or None
        email = input("E-mail (opcional): ").strip() or None
        telefone = input("Telefone (opcional): ").strip() or None

        if (perfil or "").lower() == "admin":
            print("\n💡 Nota: Perfis ADMIN enxergam automaticamente 100% das obras ativas.")
            obras_ids = None
        else:
            print("\n--- Obras Disponíveis no Banco ---")
            await listar_obras_cmd()
            obras_raw = input(
                "IDs das Obras vinculadas separados por espaço (ex: 128 129) [Enter p/ vincular à principal]: "
            ).strip()
            obras_ids = [int(x) for x in obras_raw.split()] if obras_raw else None

        unidades_raw = input("IDs das Unidades vinculadas separados por espaço (opcional): ").strip()
        unidades_ids = [int(x) for x in unidades_raw.split()] if unidades_raw else None

        await criar_ou_atualizar_usuario_cmd(
            cpf=cpf,
            nome=nome,
            senha=senha,
            perfil=perfil,
            email=email,
            telefone=telefone,
            obras_ids=obras_ids,
            unidades_ids=unidades_ids,
        )
    elif opcao == "4":
        ident = input("Informe o CPF ou ID do perfil que deseja apagar: ").strip()
        await apagar_usuario_cmd(ident)
    elif opcao == "5":
        await listar_obras_cmd()
    elif opcao == "6":
        await limpar_mocks_cmd()
    elif opcao == "7":
        print("\n--- Obras Disponíveis ---")
        await listar_obras_cmd()
        oid_raw = input("Informe o ID da Obra: ").strip()
        if not oid_raw.isdigit():
            print("[ERRO] ID da obra deve ser numérico.")
            return
        pct_raw = input("Novo percentual de conclusão (ex: 15.5) [Enter p/ não alterar]: ").strip()
        fase_raw = input("Nova fase (estrutural_geral / reformas_unidades / entrega) [Enter p/ não alterar]: ").strip()
        pct = float(pct_raw) if pct_raw else None
        fase = fase_raw if fase_raw else None
        await definir_obra_cmd(int(oid_raw), percentual=pct, fase=fase)
    else:
        print("[ERRO] Opção inválida.")


if __name__ == "__main__":
    args = parse_args()
    if args.listar:
        asyncio.run(listar_usuarios_cmd())
    elif args.listar_obras:
        asyncio.run(listar_obras_cmd())
    elif args.limpar_mocks:
        asyncio.run(limpar_mocks_cmd())
    elif args.definir_obra_percentual:
        oid, pct = args.definir_obra_percentual
        asyncio.run(definir_obra_cmd(int(oid), percentual=float(pct)))
    elif args.definir_obra_fase:
        oid, fase = args.definir_obra_fase
        asyncio.run(definir_obra_cmd(int(oid), fase=fase))
    elif args.ver:
        asyncio.run(ver_usuario_cmd(args.ver))
    elif args.apagar:
        asyncio.run(apagar_usuario_cmd(args.apagar))
    elif args.cpf:
        ativo_bool = None
        if args.ativo is not None:
            ativo_bool = args.ativo.lower() == "true"
        asyncio.run(
            criar_ou_atualizar_usuario_cmd(
                cpf=args.cpf,
                nome=args.nome,
                senha=args.senha,
                perfil=args.perfil,
                email=args.email,
                telefone=args.telefone,
                ativo=ativo_bool,
                obras_ids=args.obras,
                adicionar_obras_ids=args.adicionar_obras,
                remover_obras_ids=args.remover_obras,
                unidades_ids=args.unidades,
            )
        )
    else:
        asyncio.run(menu_interativo())
