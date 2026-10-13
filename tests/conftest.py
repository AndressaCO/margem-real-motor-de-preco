import pytest

from margem_real.channels import canais_dataframe
from margem_real.pipeline import Armazem
from margem_real.synthetic import gerar_skus, gerar_vendas


@pytest.fixture()
def dados():
    skus = gerar_skus(40, 7)
    return skus, gerar_vendas(skus, semente=7)


@pytest.fixture()
def armazem(dados):
    skus, vendas = dados
    a = Armazem()
    a.carregar_canais(canais_dataframe())
    a.carregar_skus(skus[["sku", "categoria", "custo"]])
    a.carregar_vendas(vendas)
    yield a
    a.fechar()
