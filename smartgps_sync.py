import gspread
from google.oauth2.service_account import Credentials
import requests
import json
from datetime import datetime
import os

print("=" * 60)
print("🤖 SISTEMA SMARTGPS - GITHUB ACTIONS")
print("=" * 60)

# Configurações das variáveis de ambiente
user_api_hash = os.environ['USER_API_HASH']
GOOGLE_SHEETS_URL = "https://docs.google.com/spreadsheets/d/1ViFurbM4eWQus2QnzwcbGtRd64o90Vf9N_BB8M_QdWw"
base_url = "https://sp.tracker-net.app"

def conectar_google_sheets():
    """Conecta com Google Sheets"""
    try:
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
        print(f"❌ Erro Google Sheets: {e}")
        return None

def buscar_pedidos():
    """Busca pedidos do SmartGPS"""
    print("🔍 Buscando pedidos...")
    
    todos_pedidos = []
    
    for pagina in range(1, 4):  # 3 páginas para ser rápido
        try:
            response = requests.get(
                f"{base_url}/api/get_orders",
                params={"user_api_hash": user_api_hash, "page": pagina},
                timeout=10
            )
            
            if response.status_code == 200:
                dados = response.json()
                if 'items' in dados and 'data' in dados['items']:
                    pedidos_pagina = dados['items']['data']
                    todos_pedidos.extend(pedidos_pagina)
                    print(f"   📄 Página {pagina}: {len(pedidos_pagina)} pedidos")
                    
        except Exception as e:
            print(f"   💥 Erro: {e}")
            break
    
    print(f"🎯 Total: {len(todos_pedidos)} pedidos")
    return todos_pedidos

def atualizar_sheets(worksheet, pedidos):
    """Atualiza Google Sheets"""
    print("⬆️ Atualizando planilha...")
    
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
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ]
        dados_processados.append(linha)
    
    dados_processados.sort(key=lambda x: x[0], reverse=True)
    
    cabecalhos = ['ID', 'OS', 'Cliente', 'Veículo', 'Status', 'Tipo', 'Data Criação', 'Última Atualização']
    
    worksheet.clear()
    worksheet.update(range_name='A1', values=[cabecalhos])
    if dados_processados:
        worksheet.update(range_name='A2', values=dados_processados)
    
    print(f"✅ Planilha atualizada: {len(dados_processados)} pedidos")

def main():
    """Executa sincronização"""
    print(f"🕒 {datetime.now().strftime('%d/%m %H:%M')} - INICIANDO...")
    
    try:
        worksheet = conectar_google_sheets()
        if not worksheet:
            return
        
        pedidos = buscar_pedidos()
        
        if pedidos:
            atualizar_sheets(worksheet, pedidos)
            print("🎉 Sincronização concluída!")
        else:
            print("❌ Nenhum pedido encontrado")
            
    except Exception as e:
        print(f"💥 Erro: {e}")

if __name__ == "__main__":
    main()