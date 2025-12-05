import asyncio
import aiohttp
from bs4 import BeautifulSoup
import re
import json
import time

# --- Configurações ---
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
}

def limpar_cnpj(cnpj_input):
    """Remove pontos, traços e barras do CNPJ."""
    return re.sub(r'[^0-9]', '', cnpj_input)

class BuscadorFundos:
    def __init__(self):
        self.resultados = {}

    async def buscar_anbima(self, session, cnpj):
        """
        Busca na ANBIMA com extração avançada de JSON (Next.js).
        """
        url = f"https://data.anbima.com.br/fundos/{cnpj}"
        
        try:
            async with session.get(url, headers=HEADERS, timeout=10) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # TÉCNICA AVANÇADA: Sites em Next.js (como Anbima) guardam os dados
                    # em uma tag <script id="__NEXT_DATA__">. Vamos ler isso diretamente.
                    script_next = soup.find('script', id='__NEXT_DATA__')
                    
                    dados_extraidos = {
                        "cota": "Não localizado",
                        "pl": "Não localizado",
                        "data_referencia": "N/A"
                    }

                    if script_next:
                        try:
                            json_data = json.loads(script_next.string)
                            # Navegando na estrutura complexa do JSON da Anbima
                            # O caminho abaixo é um exemplo comum, pode variar se eles mudarem o site
                            page_props = json_data.get('props', {}).get('pageProps', {})
                            fundo_data = page_props.get('fundo', {})
                            
                            if fundo_data:
                                # Tenta pegar os valores mais recentes
                                dados_extraidos['nome_fundo'] = fundo_data.get('nome', 'N/A')
                                dados_extraidos['pl'] = fundo_data.get('patrimonioLiquido', 'N/A')
                                dados_extraidos['cota'] = fundo_data.get('valorCota', 'N/A')
                                dados_extraidos['data_referencia'] = fundo_data.get('dataReferencia', 'N/A')
                                
                                status_msg = "Sucesso (Dados Extraídos via JSON Oculto)"
                            else:
                                status_msg = "Estrutura JSON mudou ou fundo não tem dados públicos"
                        except Exception as json_error:
                            status_msg = f"Erro ao ler JSON oculto: {str(json_error)}"
                    else:
                        status_msg = "Script de dados ocultos não encontrado"

                    return {
                        "fonte": "Anbima",
                        "status": status_msg,
                        "url": url,
                        "dados_completos": dados_extraidos
                    }
                elif response.status == 404:
                    return {"fonte": "Anbima", "status": "Fundo não encontrado (404)", "url": url}
                else:
                    return {"fonte": "Anbima", "status": f"Erro HTTP {response.status}", "url": url}
        except Exception as e:
            return {"fonte": "Anbima", "status": f"Erro de Conexão: {str(e)}", "url": url}

    async def buscar_vortx(self, session, cnpj):
        """
        Busca na Vórtx. 
        Nota: A Vórtx protege muito bem os dados contra scraping simples.
        """
        url = "https://www.vortx.com.br/investidor/fundos-de-investimento"
        
        try:
            async with session.get(url, headers=HEADERS, timeout=10) as response:
                # Para ter dados completos aqui, seria obrigatório usar Selenium
                # pois a Vórtx carrega a tabela via chamadas API internas protegidas.
                return {
                    "fonte": "Vórtx",
                    "status": "Acesso Portal (Dados protegidos por JS/Auth)",
                    "url": url,
                    "nota": "Para extrair PL/Cota da Vórtx, é necessário usar Selenium webdriver."
                }
        except Exception as e:
            return {"fonte": "Vórtx", "status": f"Erro: {str(e)}"}

    async def buscar_cvm(self, session, cnpj):
        """
        Busca na CVM.
        Tenta usar a API de Dados Abertos (CSV) se scraping falhar, 
        mas aqui mantemos a verificação de disponibilidade.
        """
        # URL do sistema de consulta (apenas verificação de existência)
        url = "https://cvmweb.cvm.gov.br/swb/default.asp?sg_sistema=fundosreg"
        
        try:
            async with session.get(url, headers=HEADERS, timeout=15) as response:
                if response.status == 200:
                    return {
                        "fonte": "CVM",
                        "status": "Sistema Disponível",
                        "url": url,
                        "nota": "A CVM bloqueia scraping direto de valores nesta URL antiga. Use 'Dados Abertos CVM' para baixar CSVs diários."
                    }
                return {"fonte": "CVM", "status": f"Erro {response.status}"}
        except Exception as e:
            return {"fonte": "CVM", "status": f"Erro: {str(e)}"}

    async def agregar_dados(self, cnpj):
        cnpj_limpo = limpar_cnpj(cnpj)
        print(f"--- Buscando dados completos para CNPJ: {cnpj_limpo} ---")
        
        async with aiohttp.ClientSession() as session:
            tarefa_anbima = asyncio.create_task(self.buscar_anbima(session, cnpj_limpo))
            tarefa_vortx = asyncio.create_task(self.buscar_vortx(session, cnpj_limpo))
            tarefa_cvm = asyncio.create_task(self.buscar_cvm(session, cnpj_limpo))
            
            resultados = await asyncio.gather(tarefa_anbima, tarefa_vortx, tarefa_cvm)
            
            return {
                "cnpj_buscado": cnpj,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "resultados": results_to_dict(resultados)
            }

def results_to_dict(lista_resultados):
    final = {}
    for res in lista_resultados:
        fonte = res.get("fonte", "Desconhecida")
        final[fonte] = res
    return final

# --- Execução ---
if __name__ == "__main__":
    cnpj_alvo = input("Digite o CNPJ do fundo: ")
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    dados = loop.run_until_complete(BuscadorFundos().agregar_dados(cnpj_alvo))
    
    print("\n" + "="*60)
    print("RELATÓRIO DETALHADO")
    print("="*60)
    print(json.dumps(dados, indent=4, ensure_ascii=False))
