"""Testes locais: nenhuma requisição destes testes chega ao CRM."""

import json
import unittest
from unittest.mock import MagicMock, patch

import pandas as pd
from playwright.sync_api import sync_playwright

import automacao


HTML = """<!doctype html><meta charset="utf-8">
<article data-section="avaliacoes">
  <button class="lead-rel-section__toggle" aria-expanded="true">Avaliações</button>
  <button class="lead-rel-btn-remover" onclick="document.querySelector('dialog').showModal()">Remover</button>
  <div class="lead-rel-empty" hidden>Nenhum dado disponível</div>
  <table><tbody></tbody></table>
  <button class="crm-data-grid__next" onclick="offset+=2; render()">Próxima</button>
</article>
<dialog>
  <p>Tem certeza que deseja remover o relacionamento?</p>
  <button onclick="this.closest('dialog').close()">Cancelar</button>
  <button id="confirmar">Remover</button>
</dialog>
<script>
let items=['a','b','c','d','e'], selected=new Set(), offset=0;
window.EntityListRuntime={getGrid:()=>({getSelectedRowIds:()=>[...selected]})};
function render() {
  selected.clear();
  const tbody=document.querySelector('tbody');
  tbody.innerHTML='';
  for(const id of items.slice(offset,offset+2)) {
    const tr=document.createElement('tr'); tr.dataset.rowId=id;
    const td=document.createElement('td');
    const cb=document.createElement('input');
    cb.type='checkbox'; cb.className='crm-data-grid__row-select';
    cb.onchange=()=>cb.checked?selected.add(id):selected.delete(id);
    td.append(cb); tr.append(td); tbody.append(tr);
  }
  document.querySelector('.lead-rel-empty').hidden=items.length>0;
  document.querySelector('.crm-data-grid__next').disabled=offset+2>=items.length;
}
document.querySelector('#confirmar').onclick=async()=>{
  const ids=[...selected];
  document.querySelector('dialog').close();
  const r=await fetch('/api/v1/inscricoes/teste/disassociate',{
    method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({relatedIds:ids})
  });
  const body=await r.json();
  if(r.ok && body.success) {
    items=items.filter(id=>!ids.includes(id)); offset=0; render();
  }
};
render();
</script>"""


class TestRemocao(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(headless=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()

    def setUp(self):
        self.context = self.browser.new_context()
        self.page = self.context.new_page()
        self.page.set_default_timeout(3000)
        self.chamadas = []
        self.resposta = {"success": True}

        def responder(route):
            if route.request.method == "POST":
                self.chamadas.append(route.request.post_data_json)
                route.fulfill(content_type="application/json", body=json.dumps(self.resposta))
            else:
                route.fulfill(content_type="text/html", body=HTML)

        # Intercepta todas as requisições; inclusive o POST da confirmação.
        self.context.route("**/*", responder)
        self.page.goto("https://crm.test/")

    def tearDown(self):
        self.context.close()

    def test_remove_todos_os_lotes_sem_pular_registros(self):
        total = automacao.processar_secao(self.page, "teste", "avaliacoes")
        self.assertEqual(total, 5)
        self.assertEqual([r["relatedIds"] for r in self.chamadas], [["a", "b"], ["c", "d"], ["e"]])
        self.assertEqual(self.page.locator(automacao.CHECKBOX_LINHA).count(), 0)

    def test_rejeicao_do_servidor_interrompe_remocao(self):
        self.resposta = {"success": False, "message": "Relacionamento obrigatório"}
        with self.assertRaisesRegex(RuntimeError, "Operação rejeitada"):
            automacao.processar_secao(self.page, "teste", "avaliacoes")
        self.assertEqual(len(self.chamadas), 1)
        self.assertEqual(self.page.evaluate("items.length"), 5)

    def test_validacao_pagina_sem_enviar_remocoes(self):
        total = automacao.processar_secao(self.page, "teste", "avaliacoes", validar=True)
        self.assertEqual(total, 5)
        self.assertEqual(self.chamadas, [])
        self.assertEqual(self.page.evaluate("items.length"), 5)
        self.assertEqual(self.page.evaluate("[...selected]"), [])

    def test_selecao_divergente_nao_envia_remocao(self):
        self.page.evaluate("EntityListRuntime.getGrid=()=>({getSelectedRowIds:()=>['outro-id']})")
        with self.assertRaisesRegex(RuntimeError, "seleção interna"):
            automacao.processar_secao(self.page, "teste", "avaliacoes")
        self.assertEqual(self.chamadas, [])


class TestFluxo(unittest.TestCase):
    def test_falha_na_inscricao_impede_exclusao_do_lead_e_registro_de_sucesso(self):
        df = pd.DataFrame({"ID Lead": ["lead-teste"], "id_inscricao": ["inscricao-teste"]})
        with (
            patch.object(automacao, "carregar_dataset", return_value=df),
            patch.object(automacao, "carregar_processados", return_value=set()),
            patch.object(automacao, "abrir_registro"),
            patch.object(automacao, "processar_relacionados", side_effect=RuntimeError("falha simulada")),
            patch.object(automacao, "excluir_registro") as excluir,
            patch.object(automacao, "registrar_processado") as registrar,
        ):
            with self.assertRaisesRegex(RuntimeError, "Falha em 1 lead"):
                automacao.run(MagicMock())
            excluir.assert_not_called()
            registrar.assert_not_called()


if __name__ == "__main__":
    unittest.main()
