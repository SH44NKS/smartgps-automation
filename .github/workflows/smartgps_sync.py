import gspread
from google.oauth2.service_account import Credentials
import requests
import json
from datetime import datetime
import os
import sys

print("=" * 60)
print("🤖 SISTEMA SMARTGPS - GITHUB ACTIONS")
print("=" * 60)

def debug_info():
    """Mostra informações de debug"""
    print("🔧 DEBUG INFO:")
    print(f"   Python: {sys.version}")
    print(f"   USER_API_HASH exists: {'USER_API_HASH' in os.environ}")
    print(f"   GOOGLE_CREDENTIALS exists: {'GOOGLE_CREDENTIALS' in os.environ}")
    
    if 'USER_API_HASH' in os.environ:
        hash_val = os.environ['USER_API_HASH']
        print(f"   USER_API_HASH: {hash_val[:10]}...{hash_val[-10:]}")
    
    if 'GOOGLE_CREDENTIALS' in os.environ:
        creds = os.environ['GOOGLE_CREDENTIALS']
        print(f"   GOOGLE_CREDENTIALS: {len(creds)} chars")
    
    print()

try:
    # Configurações
    user_api_hash = os.environ['USER_API_HASH']
    GOOGLE_SHEETS_URL = "https://docs.google.com/spreadsheets/d/1ViFurbM4eWQus2QnzwcbGtRd64o90Vf9N_BB8M_QdWw"
    base_url = "https://sp.tracker-net.app"

    # Debug
    debug_info()

    def conectar_google_sheets():
        """Conecta com Google Sheets"""
        try:
            print("🔐 Tentando conectar ao Google Sheets...")
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

    def buscar_pedidos():
        """Busca pedidos do SmartGPS"""
        print("🔍 Buscando pedidos do SmartGPS...")
        
        todos_pedidos = []
        
        for pagina in range(1, 3):  # 2 páginas para teste
            try:
                print(f"   📄 Buscando página {pagina}...")
                response = requests.get(
                    f"{base_url}/api/get_orders",
                    params={"user_api_hash": user_api_hash, "page": pagina},
                    timeout=15
                )
                
                print(f"   📊 Status: {response.status_code}")
                
                if response.status_code == 200:
                    dados = response.json()
                    if 'items' in dados and 'data' in dados['items']:
                        pedidos_pagina = dados['items']['data']
                        todos_pedidos.extend(pedidos_pagina)
                        print(f"   ✅ Página {pagina}: {len(pedidos_pagina)} pedidos")
                    else:
                        print(f"   ❌ Estrutura inesperada: {list(dados.keys())}")
                else:
                    print(f"   ❌ Erro HTTP: {response.text[:100]}")
                    break
                    
            except Exception as e:
                print(f"   💥 Erro: {e}")
                break
        
        print(f"🎯 Total encontrado: {len(todos_pedidos)} pedidos")
        return todos_pedidos

    def main():
        """Executa sincronização"""
        print(f"🕒 {datetime.now().strftime('%d/%m %H:%M')} - INICIANDO SINCRONIZAÇÃO...")
        
        try:
            worksheet = conectar_google_sheets()
            if not worksheet:
                print("❌ Não foi possível conectar ao Google Sheets")
                return
            
            pedidos = buscar_pedidos()
            
            if pedidos:
                print("⬆️ Atualizando Google Sheets...")
                
                # Processar dados
                dados_processados = []
                for pedido in pedidos[:5]:  # Apenas 5 para teste
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
                
                cabecalhos = ['ID', 'OS', 'Cliente', 'Veículo', 'Status', 'Tipo', 'Data Criação', 'Última Atualização']
                
                worksheet.clear()
                worksheet.update(range_name='A1', values=[cabecalhos])
                if dados_processados:
                    worksheet.update(range_name='A2', values=dados_processados)
                
                print(f"✅ Google Sheets atualizado: {len(dados_processados)} pedidos")
                print("🎉 Sincronização concluída com sucesso!")
            else:
                print("❌ Nenhum pedido encontrado para atualizar")
                
        except Exception as e:
            print(f"💥 Erro na sincronização: {e}")

    if __name__ == "__main__":
        main()

except KeyError as e:
    print(f"❌ ERRO CRÍTICO: Variável de ambiente faltando: {e}")
    print("💡 Verifique se configurou os Secrets no GitHub:")
    print("   - USER_API_HASH")
    print("   - GOOGLE_CREDENTIALS")
    sys.exit(1)
except Exception as e:
    print(f"💥 ERRO INESPERADO: {e}")
    sys.exit(1)
