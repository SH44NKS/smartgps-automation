import gspread
from google.oauth2.service_account import Credentials
import requests
import json
from datetime import datetime
import os
import sys

print("=" * 60)
print("🤖 SISTEMA SMARTGPS - ORDENAÇÃO CORRIGIDA")
print("=" * 60)

# Configurações
user_api_hash = os.environ['USER_API_HASH']
GOOGLE_SHEETS_URL = "https://docs.google.com/spreadsheets/d/1ViFurbM4eWQus2QnzwcbGtRd64o90Vf9N_BB8M_QdWw"
base_url = "https://sp.tracker-net.app"

def conectar_google_sheets():
    """Conecta com Google Sheets"""
    try:
        print("🔐 Conectando ao Google Sheets...")
        creds_json = os.environ['GOOGLE_CREDENTIALS']
        creds_dict = json.loads(creds_json)
        
        SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        client = gspread.authorize(creds)
        planilha = client.open_by_url(GOOGLE_SHEETS_URL)
        worksheet = planilha.sheet1
        print("✅ Conectado ao Google Sheets!")
        return worksheet
    except Exception as e:
        print(f"❌ Erro ao conectar Google Sheets: {e}")
        return None

def buscar_todas_as_paginas():
    """Busca TODAS as páginas disponíveis"""
    print("🔍 Buscando TODOS os pedidos...")
    
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
                    
                    if not pedidos_pagina:  # Página vazia
                        break
                    
                    todos_pedidos.extend(pedidos_pagina)
                    
                    # Pega o total de páginas na primeira requisição
                    if total_paginas is None:
                        total_paginas = dados['items'].get('last_page', 1)
                        print(f"{len(pedidos_pagina)} pedidos (Total: ~{total_paginas} páginas)")
                    else:
                        print(f"{len(pedidos_pagina)} pedidos")
                    
                    # Verifica se chegou na última página
                    if pagina >= total_paginas or not dados['items'].get('next_page_url'):
                        break
                    
                    pagina += 1
                    
                else:
                    break
            else:
                print(f"erro {response.status_code}")
                break
                
        except Exception as e:
            print(f"erro: {e}")
            break
    
    print(f"🎯 Total encontrado: {len(todos_pedidos)} pedidos em {pagina} páginas")
    return todos_pedidos

def atualizar_google_sheets(worksheet, pedidos):
    """Atualiza o Google Sheets com ordenação por data"""
    print("⬆️ Atualizando Google Sheets...")
    
    # Processa os dados
    dados_processados = []
    for pedido in pedidos:
        status_map = {'A': 'Ativo', 'C': 'Cancelado', 'CD': 'Concluído', 'P': 'Pendente'}
        tipo_map = {'1': 'Instalação', '2': 'Manutenção', '3': 'Retirada'}
        
        # Pega a data para ordenação
        data_criacao = pedido.get('created_at', '')
        
        linha = [
            pedido.get('id'),
            f"OS-{pedido.get('id')}",
            pedido.get('client_name', ''),
            pedido.get('plate_number', ''),
            status_map.get(pedido.get('status'), pedido.get('status_text', '')),
            tipo_map.get(pedido.get('type_order'), 'Outros'),
            data_criacao,  # Mantém a string original para exibição
            pedido.get('client_tab_client_phone', ''),
            pedido.get('client_tab_client_address_city', ''),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ]
        dados_processados.append((data_criacao, linha))
    
    # Ordena por DATA (mais recente primeiro)
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

def criar_resumo(pedidos):
    """Cria um resumo estatístico"""
    if not pedidos:
        return
    
    # Contadores
    por_status = {}
    por_tipo = {}
    
    for pedido in pedidos:
        status = pedido.get('status_text', 'Desconhecido')
        tipo = pedido.get('type_order', '0')
        
        por_status[status] = por_status.get(status, 0) + 1
        
        tipo_map = {'1': 'Instalação', '2': 'Manutenção', '3': 'Retirada'}
        tipo_nome = tipo_map.get(tipo, 'Outros')
        por_tipo[tipo_nome] = por_tipo.get(tipo_nome, 0) + 1
    
    print(f"\n📊 RESUMO ESTATÍSTICO:")
    print(f"   📦 Total de pedidos: {len(pedidos)}")
    print(f"   📋 Por status:")
    for status, count in por_status.items():
        print(f"      - {status}: {count}")
    
    print(f"   🔧 Por tipo:")
    for tipo, count in por_tipo.items():
        print(f"      - {tipo}: {count}")

def main():
    """Executa sincronização completa"""
    print(f"🕒 {datetime.now().strftime('%d/%m/%Y %H:%M')} - INICIANDO BACKUP COMPLETO...")
    
    try:
        # 1. Conectar Google Sheets
        worksheet = conectar_google_sheets()
        if not worksheet:
            print("❌ Falha na conexão com Google Sheets")
            return
        
        # 2. Buscar TODOS os pedidos
        pedidos = buscar_todas_as_paginas()
        
        if not pedidos:
            print("❌ Nenhum pedido encontrado")
            return
        
        # 3. Atualizar Google Sheets (agora ordenado por data)
        atualizar_google_sheets(worksheet, pedidos)
        
        # 4. Mostrar resumo
        criar_resumo(pedidos)
        
        print(f"\n🎉 BACKUP COMPLETO CONCLUÍDO!")
        print(f"📊 {len(pedidos)} pedidos sincronizados")
        print(f"📅 Ordenação: Mais recentes primeiro")
        print(f"⏰ Próxima execução automática: 5 minutos")
        
    except Exception as e:
        print(f"💥 Erro na sincronização: {e}")

if __name__ == "__main__":
    main()
