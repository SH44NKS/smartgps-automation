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
                    print(f"{len(pedidos_pagina)} pedidos")
                    
                    # Verifica se há mais páginas
                    if not dados['items'].get('next_page_url'):
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

def ordenar_pedidos_por_data(pedidos):
    """Ordena pedidos por data de criação (mais recente primeiro)"""
    print("📅 Ordenando pedidos por data...")
    
    # Filtra pedidos com data válida e converte para datetime
    pedidos_com_data = []
    pedidos_sem_data = []
    
    for pedido in pedidos:
        data_str = pedido.get('created_at', '')
        if data_str and data_str != '0000-00-00 00:00:00':
            try:
                # Converte string para datetime para ordenação
                data_dt = datetime.strptime(data_str, "%Y-%m-%d %H:%M:%S")
                pedidos_com_data.append((data_dt, pedido))
            except:
                pedidos_sem_data.append(pedido)
        else:
            pedidos_sem_data.append(pedido)
    
    # Ordena por data (mais recente primeiro)
    pedidos_com_data.sort(key=lambda x: x[0], reverse=True)
    
    # Junta tudo: pedidos com data (ordenados) + pedidos sem data
    pedidos_ordenados = [pedido for _, pedido in pedidos_com_data] + pedidos_sem_data
    
    print(f"   ✅ {len(pedidos_com_data)} pedidos com data ordenados")
    print(f"   ⚠️  {len(pedidos_sem_data)} pedidos sem data")
    
    return pedidos_ordenados

def atualizar_google_sheets(worksheet, pedidos):
    """Atualiza o Google Sheets com pedidos ordenados"""
    print("⬆️ Atualizando Google Sheets...")
    
    # Processa os dados
    dados_processados = []
    for pedido in pedidos:
        status_map = {'A': 'Ativo', 'C': 'Cancelado', 'CD': 'Concluído', 'P': 'Pendente'}
        tipo_map = {'1': 'Instalação', '2': 'Manutenção', '3': 'Retirada'}
        
        linha = [
            pedido.get('id'),
            f"OS-{pedido.get('id')}",
            pedido.get('client_name', ''),
            pedido.get('plate_number', ''),
            status_map.get(pedido.get('status'), pedido.get('status_text', '')),
            tipo_map.get(pedido.get('type_order'), 'Outros'),
            pedido.get('created_at', ''),
            pedido.get('client_tab_client_phone', ''),
            pedido.get('client_tab_client_address_city', ''),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ]
        dados_processados.append(linha)
    
    # Cabeçalhos
    cabecalhos = [
        'ID', 'OS', 'Cliente', 'Veículo', 'Status', 'Tipo', 
        'Data Criação', 'Telefone', 'Cidade', 'Última Atualização'
    ]
    
    # Atualiza a planilha
    worksheet.clear()
    worksheet.update(range_name='A1', values=[cabecalhos])
    if dados_processados:
        worksheet.update(range_name='A2', values=dados_processados)
    
    print(f"✅ Google Sheets atualizado: {len(dados_processados)} pedidos")
    print("📅 ORDENAÇÃO: Mais recentes no TOPO")

def main():
    """Executa sincronização completa"""
    print(f"🕒 {datetime.now().strftime('%d/%m/%Y %H:%M')} - INICIANDO...")
    
    try:
        # 1. Conectar Google Sheets
        worksheet = conectar_google_sheets()
        if not worksheet:
            return
        
        # 2. Buscar TODOS os pedidos
        pedidos = buscar_todas_as_paginas()
        
        if not pedidos:
            print("❌ Nenhum pedido encontrado")
            return
        
        # 3. ORDENAR por data (MAIS IMPORTANTE!)
        pedidos_ordenados = ordenar_pedidos_por_data(pedidos)
        
        # 4. Atualizar Google Sheets
        atualizar_google_sheets(worksheet, pedidos_ordenados)
        
        print(f"\n🎉 SINCRONIZAÇÃO CONCLUÍDA!")
        print(f"📊 {len(pedidos)} pedidos processados")
        print(f"📅 Ordenação: MAIS RECENTES NO TOPO ✅")
        
    except Exception as e:
        print(f"💥 Erro: {e}")

if __name__ == "__main__":
    main()
