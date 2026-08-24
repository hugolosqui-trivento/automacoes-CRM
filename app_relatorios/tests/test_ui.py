import pandas as pd

from ui import filtrar_por_unidade_lead


def test_filtra_dataframe_por_unidade_lead():
    dataframe = pd.DataFrame(
        {"Unidade Lead": ["Itabirito", "Altamira", None], "valor": [1, 2, 3]}
    )

    filtrado = filtrar_por_unidade_lead(dataframe, ["Altamira"])

    assert filtrado["valor"].tolist() == [2]
    assert len(filtrar_por_unidade_lead(dataframe, [])) == 3


def test_filtro_nao_altera_dataframe_sem_unidade_lead():
    duplicidades = pd.DataFrame({"valor": [1, 2]})

    assert len(filtrar_por_unidade_lead(duplicidades, ["Altamira"])) == 2
