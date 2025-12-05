# Cell
import streamlit as st
import asyncio
import aiohttp
from bs4 import BeautifulSoup
import re
import time

# Configuração da página para parecer um app
st.set_page_config(
    page_title="Buscador de Fundos",
    page_icon="💰",
    layout="centered"
)

# --- Lógica de Negócio (Backend) ---

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
}

def limpar_cnpj(cnpj_input):
    return re.sub(r'[^0-9]', '', cnpj_input)

async def buscar_anbima(session, cnpj):
    url = f"https://data.anbima.com.br/fundos/{cnpj}"
    try:
        async with session.get(url, headers=HEADERS, timeout=10) as response:
            if response.status == 200:
                # Simulação de sucesso para demo
                return {
                    "fonte": "Anbima",
                    "status": "Online",
                    "url": url,
                    "info": "Página acessada com sucesso (HTML)"
                }
            return {"fonte": "Anbima", "status": f"Erro {response.status}", "url": url}
    except Exception as e:
        return {"fonte": "Anbima", "status": "Erro de Conexão", "detalhe": str(e)}

async def buscar_vortx(session, cnpj):
    url = "https://www.vortx.com.br/investidor/fundos-de-investimento"
    try:
        async with session.get(url, headers=HEADERS, timeout=10) as response:
            return {
                "fonte": "Vórtx",
                "status": "Online",
                "url": url,
                "info": "Portal acessado (Requer navegação complexa)"
            }
    except Exception as e:
        return {"fonte": "Vórtx", "status": "Erro", "detalhe": str(e)}

async def buscar_cvm(session, cnpj):
    url = "https://cvmweb.cvm.gov.br/swb/default.asp?sg_sistema=fundosreg"
    try:
        async with session.get(url, headers=HEADERS, timeout=15) as response:
            if response.status == 200:
                return {
                    "fonte": "CVM",
                    "status": "Online",
                    "url": url,
                    "info": "Sistema legado acessado"
                }
            return {"fonte": "CVM", "status": f"Erro {response.status}"}
    except Exception as e:
        return {"fonte": "CVM", "status": "Erro", "detalhe": str(e)}

async def processar_buscas(cnpj):
    cnpj_limpo = limpar_cnpj(cnpj)
    
    async with aiohttp.ClientSession() as session:
        # Cria tarefas simultâneas
        tarefa_anbima = asyncio.create_task(buscar_anbima(session, cnpj_limpo))
        tarefa_vortx = asyncio.create_task(buscar_vortx(session, cnpj_limpo))
        tarefa_cvm = asyncio.create_task(buscar_cvm(session, cnpj_limpo))
        
        # Espera todas terminarem
        resultados = await asyncio.gather(tarefa_anbima, tarefa_vortx, tarefa_cvm)
        return resultados

# --- Interface Gráfica (Frontend) ---

st.title("🔎 Agregador de Fundos")
st.markdown("Busque informações de fundos na **Anbima**, **Vórtx** e **CVM** simultaneamente.")

cnpj_input = st.text_input("Digite o CNPJ do Fundo", placeholder="00.000.000/0000-00")

if st.button("Pesquisar Dados", type="primary"):
    if not cnpj_input:
        st.warning("Por favor, digite um CNPJ.")
    else:
        with st.spinner('Consultando as 3 bases de dados ao mesmo tempo...'):
            # Bridge entre Streamlit (síncrono) e aiohttp (assíncrono)
            try:
                # Cria um novo event loop para rodar a função async
                resultados = asyncio.run(processar_buscas(cnpj_input))
                
                st.success("Busca finalizada!")
                
                # Exibição dos resultados em colunas
                col1, col2, col3 = st.columns(3)
                
                fontes = ["Anbima", "Vórtx", "CVM"]
                cols = [col1, col2, col3]
                
                # Mapeia resultados para as colunas
                for i, res in enumerate(resultados):
                    with cols[i]:
                        st.subheader(res.get('fonte', fontes[i]))
                        
                        status = res.get('status', 'Erro')
                        if "Erro" in status:
                            st.error(status)
                        else:
                            st.success(status)
                        
                        st.caption(f"URL: {res.get('url', '')}")
                        st.json(res)
                        
            except Exception as e:
                st.error(f"Ocorreu um erro crítico na execução: {e}")

st.markdown("---")
st.caption("Nota: Este app apenas verifica a conectividade e baixa o HTML bruto. Dados específicos (PL/Cota) requerem parsers customizados para cada dia.")

