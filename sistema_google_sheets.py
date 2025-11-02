import gspread
from google.oauth2.service_account import Credentials
import requests
import pandas as pd
import json
import time
from datetime import datetime
import os

print("=" * 60)
print("🤖 SISTEMA AUTOMÁTICO SMARTGPS + GOOGLE SHEETS")
print("=" * 60)

# Configurações
user_api_hash = "$2y$10$Dj9J.uuRlDGFslSzD7dze.Ou6W88DjuA/Zlg6R7Le5yJG0WyrwdKS"
base_url = "https://sp.tracker-net.app"
GOOGLE_SHEETS_URL = "https://docs.google.com/spreadsheets/d/1ViFurbM4eWQus2QnzwcbGtRd64o90Vf9N_BB8M_QdWw"

# Arquivos de controle
ARQUIVO_ULTIMOS_IDS = "ultimos_ids.txt"

def conectar_google_sheets():
    """Conecta com Google Sheets"""
    try:
        SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
        creds = Credentials.from_service_account_file('credenciais.json', scopes=SCOPES)
        client = gspread.authorize(creds)
        planilha = client.open_by_url(GOOGLE_SHEETS_URL)
        worksheet = planilha.sheet1
        print("✅ Conectado ao Google Sheets!")
        return worksheet
    except Exception as e:
        print(f"❌ Erro ao conectar Google Sheets: {e}")
        return None

def carregar_ultimos_ids():
    """Carrega os IDs que já conhecemos"""
    try:
        with open(ARQUIVO_ULTIMOS_IDS, 'r') as f:
            return set(map(int, f.read().splitlines()))
    except:
        return set()

def salvar_ultimos_ids(ids_set):
    """Salva os IDs conhecidos"""
    with open(ARQUIVO_ULTIMOS_IDS, 'w') as f:
        for id_num in sorted(ids_set):
            f.write(f"{id_num}\n")

def buscar_todas_as_paginas():
    """Busca TODAS as páginas disponíveis"""
    print("🔍 Buscando pedidos do SmartGPS...")
    
    todos_pedidos = []
    pagina = 1
    total_paginas = None
    
    while True:
        try:
            print(f"   📄 Página {pagina}...", end=" ")
            
            response = requests.get(
                f"{base_url}/api/get_orders",
                params={"user_api_hash": user_api_hash, "page": pagina},
                timeout=20
            )
            
            if response.status_code == 200:
                dados = response.json()
                
                if 'items' in dados and 'data' in dados['items']:
                    pedidos_pagina = dados['items']['data']
                    
                    if not pedidos_pagina:
                        break
                    
                    todos_pedidos.extend(pedidos_pagina)
                    
                    if total_paginas is None:
                        total_paginas = dados['items'].get('last_page', 1)
                        print(f"{len(pedidos_pagina)} pedidos (Total: ~{total_paginas} páginas)")
                    else:
                        print(f"{len(pedidos_pagina)} pedidos")
                    
                    if pagina >= total_paginas or not dados['items'].get('next_page_url'):
                        break
                    
                    pagina += 1
                    time.sleep(0.2)
                    
                else:
                    break
            else:
                print(f"❌ Erro {response.status_code}")
                break
                
        except Exception as e:
            print(f"💥 Erro: {e}")
            break
    
    print(f"🎯 Total encontrado: {len(todos_pedidos)} pedidos")
    return todos_pedidos

def atualizar_google_sheets(worksheet, pedidos):
    """Atualiza o Google Sheets com todos os pedidos"""
    print("⬆️ Atualizando Google Sheets...")
    
    # Processa os dados
    dados_processados = []
    for pedido in pedidos:
        status_map = {'A': 'Ativo', 'C': 'Cancelado', 'CD': 'Concluído', 'P': 'Pendente'}
        tipo_map = {'1': 'Instalação', '2': 'Manutenção', '3': 'Retirada'}
        
        # Converte a data para objeto datetime para ordenação
        data_criacao = pedido.get('created_at', '')
        
        linha = [
            pedido.get('id'),
            f"OS-{pedido.get('id')}",
            pedido.get('client_name', ''),
            pedido.get('plate_number', ''),
            status_map.get(pedido.get('status'), pedido.get('status_text', '')),
            tipo_map.get(pedido.get('type_order'), 'Outros'),
            data_criacao,  # Mantém a string original
            pedido.get('client_tab_client_phone', ''),
            pedido.get('client_tab_client_address_city', ''),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ]
        dados_processados.append((data_criacao, linha))  # Guarda a data para ordenação
    
    # Ordena por DATA (mais recente primeiro)
    # Pedidos sem data vão para o final
    dados_processados.sort(key=lambda x: x[0] if x[0] else '0000-00-00 00:00:00', reverse=True)
    
    # Remove a data de ordenação, mantém apenas os dados
    dados_finais = [linha for _, linha in dados_processados]
    
    # Cabeçalhos
    cabecalhos = [
        'ID', 'OS', 'Cliente', 'Veículo', 'Status', 'Tipo', 
        'Data Criação', 'Telefone', 'Cidade', 'Última Atualização'
    ]
    
    # Atualiza a planilha
    worksheet.clear()
    worksheet.update(range_name='A1', values=[cabecalhos])
    if dados_finais:
        worksheet.update(range_name='A2', values=dados_finais)
    
    print(f"✅ Google Sheets atualizado: {len(dados_finais)} pedidos")
    print(f"📅 Ordenação: Mais recentes primeiro")

def executar_sincronizacao():
    """Executa uma sincronização completa"""
    print(f"\n🕒 {datetime.now().strftime('%H:%M:%S')} - SINCRONIZANDO...")
    
    try:
        # 1. Conectar Google Sheets
        worksheet = conectar_google_sheets()
        if not worksheet:
            return 0
        
        # 2. Carregar IDs conhecidos
        ids_conhecidos = carregar_ultimos_ids()
        print(f"   📊 IDs conhecidos: {len(ids_conhecidos)}")
        
        # 3. Buscar todos os pedidos
        todos_pedidos = buscar_todas_as_paginas()
        
        if not todos_pedidos:
            print("   ❌ Nenhum pedido encontrado")
            return 0
        
        # 4. Encontrar pedidos novos
        ids_atuais = set(pedido['id'] for pedido in todos_pedidos)
        pedidos_novos = [p for p in todos_pedidos if p['id'] not in ids_conhecidos]
        
        if pedidos_novos:
            print(f"   🎉 {len(pedidos_novos)} NOVO(S) PEDIDO(S)!")
            
            # Mostra os novos
            print("\n   📋 PEDIDOS NOVOS:")
            for pedido in pedidos_novos[:3]:
                print(f"      - OS-{pedido['id']}: {pedido.get('client_name')} | {pedido.get('plate_number')} | {pedido.get('status_text')}")
            
            if len(pedidos_novos) > 3:
                print(f"      ... e mais {len(pedidos_novos) - 3} pedidos")
        
        # 5. Atualizar Google Sheets (sempre atualiza tudo)
        atualizar_google_sheets(worksheet, todos_pedidos)
        
        # 6. Atualizar IDs conhecidos
        salvar_ultimos_ids(ids_atuais)
        
        return len(pedidos_novos)
        
    except Exception as e:
        print(f"   💥 Erro na sincronização: {e}")
        return 0

def modo_automatico_google_sheets():
    """Modo automático com Google Sheets"""
    print("🤖 MODO AUTOMÁTICO GOOGLE SHEETS ATIVADO")
    print("📡 Sincronizando a cada 5 minutos...")
    print("⏸️  Pressione Ctrl+C para parar")
    print("-" * 50)
    
    try:
        contador = 0
        while True:
            novos = executar_sincronizacao()
            contador += 1
            
            print(f"   🔄 Sincronização #{contador} concluída")
            if novos > 0:
                print(f"   🔔 {novos} novo(s) pedido(s) adicionado(s) ao Google Sheets!")
            
            print("   😴 Aguardando 5 minutos...")
            print("-" * 50)
            
            time.sleep(300)  # 5 minutos
            
    except KeyboardInterrupt:
        print("\n🛑 Sistema automático interrompido")

def main():
    """Menu principal"""
    print("\n🎛️  OPÇÕES:")
    print("1. 🔄 Sincronizar uma vez")
    print("2. 🤖 Ativar modo automático (5 minutos)")
    print("3. 📊 Ver status")
    
    opcao = input("\nEscolha uma opção (1-3): ").strip()
    
    if opcao == "1":
        novos = executar_sincronizacao()
        print(f"\n✅ Sincronização concluída! {novos} novos pedidos.")
    elif opcao == "2":
        modo_automatico_google_sheets()
    elif opcao == "3":
        ids = carregar_ultimos_ids()
        print(f"📊 Status: {len(ids)} IDs conhecidos")
        print(f"🔗 Planilha: {GOOGLE_SHEETS_URL}")
    else:
        print("❌ Opção inválida")
    
    print("\n⏰ Fechando em 10 segundos...")
    time.sleep(10)

if __name__ == "__main__":

    main()
